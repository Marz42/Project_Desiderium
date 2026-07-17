"""G4: public YouTube performance feedback loop (association only, not causal).

Fetches public metrics for published videos at configured age windows
(initial/24h/72h/7d), and computes a PerformanceRatio against the team's own
channel baseline velocity by format x age bucket (falling back to a team-wide
aggregate with low confidence when the granular sample is too small).
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.youtube.adapter import YouTubeAdapter
from app.adapters.youtube.client import YouTubeClient
from app.adapters.youtube.normalize import normalize_youtube_video
from app.config import Settings, get_settings
from app.domain.publication_metrics import (
    WINDOW_ORDER,
    classify_format,
    compute_performance_ratio,
    is_late_backfill,
    is_window_due,
    median_velocity,
)
from app.domain.trend_metrics import (
    age_bucket_key_to_model,
    assign_age_bucket,
    baseline_confidence_label,
    video_age_hours,
)
from app.models import (
    AgeBucket,
    BaselineConfidence,
    CreativeFormat,
    Platform,
    PublicationFetchStatus,
    PublicationRecord,
    PublicationWindowKey,
)
from app.repositories.publication_records import (
    PublicationMetricSnapshotRepository,
    PublicationRecordRepository,
)
from app.services.scoring_config import ScoringConfig, get_scoring_config

logger = logging.getLogger(__name__)


class PublicationMetricsService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        settings: Settings | None = None,
        config: ScoringConfig | None = None,
    ) -> None:
        self._session = session
        self._records = PublicationRecordRepository(session)
        self._snapshots = PublicationMetricSnapshotRepository(session)
        self._settings = settings or get_settings()
        self._config = config or get_scoring_config()

    def _build_adapter(self) -> YouTubeAdapter | None:
        if not self._settings.youtube_api_key:
            return None
        client = YouTubeClient(
            self._settings.youtube_api_key,
            max_search_calls=self._settings.youtube_max_search_calls,
            daily_quota_limit=self._settings.youtube_daily_quota_limit,
        )
        return YouTubeAdapter(client)

    async def attempt_immediate_capture(self, record: PublicationRecord) -> None:
        """Best-effort enrichment right after publish. Never raises.

        API failure must not roll back the angle status transition; the
        record is left retryable (fetch_status=FAILED/PENDING) for the
        scheduled job.
        """
        adapter = self._build_adapter()
        if adapter is None:
            return
        try:
            await self._process_record(record, adapter=adapter, now=datetime.now(UTC))
        except Exception as exc:  # noqa: BLE001 - isolation: publish must not fail
            logger.warning("publication immediate capture failed for %s: %s", record.id, exc)
            self._record_failure(record, exc, now=datetime.now(UTC))
            await self._session.flush()
        finally:
            await adapter.close()

    async def run_due_windows(self) -> dict[str, int]:
        """Scheduled job entry point: fetch metrics for all due windows.

        Per-record failures are isolated and do not stop processing of other
        records.
        """
        summary = {"processed": 0, "captured": 0, "errors": 0, "skipped_no_api_key": 0}
        adapter = self._build_adapter()
        if adapter is None:
            logger.info("publication_metrics job skipped: no YouTube API key configured")
            summary["skipped_no_api_key"] = 1
            return summary

        try:
            records = await self._records.list_published_for_metrics()
            now = datetime.now(UTC)
            for record in records:
                summary["processed"] += 1
                try:
                    captured = await self._process_record(record, adapter=adapter, now=now)
                    summary["captured"] += captured
                except Exception as exc:  # noqa: BLE001 - per-record error isolation
                    logger.warning("publication_metrics record %s failed: %s", record.id, exc)
                    self._record_failure(record, exc, now=now)
                    summary["errors"] += 1
                await self._session.flush()
            await self._session.commit()
        finally:
            await adapter.close()
        return summary

    async def _due_windows(
        self,
        record: PublicationRecord,
        now: datetime,
    ) -> list[tuple[PublicationWindowKey, int]]:
        anchor = record.published_at or record.created_at
        anchor_age = video_age_hours(anchor, now)
        existing = {snap.window_key for snap in record.metric_snapshots}
        existing_positions = [
            index for index, key in enumerate(WINDOW_ORDER) if key in existing
        ]
        latest_existing_position = max(existing_positions, default=-1)
        due: list[tuple[PublicationWindowKey, int]] = []
        for index, (key, target_hours) in enumerate(
            zip(WINDOW_ORDER, self._config.publication.windows_hours),
        ):
            if key in existing:
                continue
            if index <= latest_existing_position:
                continue
            if is_window_due(anchor_age, target_hours):
                due.append((key, target_hours))
        # A late observation is current data, not fabricated history. Capture
        # only the latest matured window and leave older missed windows absent.
        return due[-1:] if due else []

    async def _process_record(
        self,
        record: PublicationRecord,
        *,
        adapter: YouTubeAdapter,
        now: datetime,
    ) -> int:
        if not record.external_video_id:
            return 0
        due = await self._due_windows(record, now)
        if not due:
            return 0

        details = await adapter.fetch_item_details([record.external_video_id])
        if not details:
            raise RuntimeError(f"video {record.external_video_id} not found via public API")
        normalized = normalize_youtube_video(details[0])

        if record.channel_external_id is None:
            record.channel_external_id = normalized.get("channel_external_id")
        if record.platform is None:
            record.platform = Platform.YOUTUBE
        published_at = normalized.get("published_at")
        if published_at is not None:
            record.published_at = published_at
        duration_seconds = normalized.get("duration_seconds")
        if record.format is None and duration_seconds is not None:
            record.format = classify_format(duration_seconds)

        anchor = record.published_at or record.created_at
        metrics = normalized.get("metrics", {})
        views = int(metrics.get("views") or 0)
        likes = metrics.get("likes")
        comments = metrics.get("comments")

        captured = 0
        for window_key, target_hours in due:
            age_hours = video_age_hours(anchor, now)
            age_bucket = age_bucket_key_to_model(assign_age_bucket(age_hours))
            late = is_late_backfill(
                age_hours,
                target_hours,
                self._config.publication.late_backfill_grace_hours,
            )
            baseline_velocity: float | None = None
            baseline_sample_count: int | None = None
            baseline_confidence: BaselineConfidence | None = None
            performance_ratio: float | None = None

            if record.format is not None and age_bucket is not None:
                (
                    baseline_velocity,
                    baseline_sample_count,
                    baseline_confidence,
                ) = await self._compute_baseline(
                    format=record.format,
                    age_bucket=age_bucket,
                    exclude_record_id=record.id,
                )
                if baseline_velocity is not None:
                    velocity = views / max(age_hours, self._config.min_age_hours)
                    performance_ratio = compute_performance_ratio(
                        velocity, baseline_velocity, self._config.epsilon
                    )

            await self._snapshots.upsert(
                publication_record_id=record.id,
                window_key=window_key,
                captured_at=now,
                video_age_hours=age_hours,
                age_bucket=age_bucket,
                views=views,
                likes=likes,
                comments=comments,
                source="youtube_public",
                late_backfill=late,
                baseline_velocity=baseline_velocity,
                baseline_sample_count=baseline_sample_count,
                baseline_confidence=baseline_confidence,
                performance_ratio=performance_ratio,
                baseline_version=self._config.publication.baseline_version,
                calculated_at=now,
            )
            captured += 1

        record.fetch_status = PublicationFetchStatus.SUCCESS
        record.last_fetch_error = None
        record.last_fetched_at = now
        record.consecutive_fetch_failures = 0
        record.next_retry_at = None
        record.terminal_fetch_failure = False
        await self._session.flush()
        return captured

    def _record_failure(
        self,
        record: PublicationRecord,
        exc: Exception,
        *,
        now: datetime,
    ) -> None:
        record.fetch_status = PublicationFetchStatus.FAILED
        record.last_fetch_error = str(exc)[:500]
        record.last_fetched_at = now
        record.consecutive_fetch_failures = (record.consecutive_fetch_failures or 0) + 1
        cfg = self._config.publication
        record.terminal_fetch_failure = (
            record.consecutive_fetch_failures >= cfg.max_consecutive_failures
        )
        backoff_multiplier = 2 ** max(record.consecutive_fetch_failures - 1, 0)
        record.next_retry_at = now + timedelta(
            hours=cfg.retry_backoff_hours * backoff_multiplier,
        )

    async def _compute_baseline(
        self,
        *,
        format: CreativeFormat,
        age_bucket: AgeBucket,
        exclude_record_id: uuid.UUID,
    ) -> tuple[float | None, int | None, BaselineConfidence | None]:
        cfg = self._config
        team_ids = cfg.publication.team_channel_ids

        granular = await self._snapshots.list_baseline_candidates(
            format=format,
            age_bucket=age_bucket,
            team_channel_ids=team_ids,
            exclude_record_id=exclude_record_id,
        )
        if len(granular) >= cfg.baselines.confidence_low_min:
            velocity = median_velocity(granular, cfg.min_age_hours)
            _, confidence = baseline_confidence_label(len(granular), config=cfg)
            return velocity, len(granular), confidence

        aggregate = await self._snapshots.list_aggregate_candidates(
            team_channel_ids=team_ids,
            exclude_record_id=exclude_record_id,
        )
        if not aggregate:
            return None, None, None
        velocity = median_velocity(aggregate, cfg.min_age_hours)
        return velocity, len(aggregate), BaselineConfidence.LOW
