"""Channel baseline computation and persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.trend_metrics import (
    VideoMetricsInput,
    breakout_ratio,
    compute_channel_baselines,
    global_baseline_by_bucket,
)
from app.models import Platform
from app.repositories.baselines import (
    BaselinesRepository,
    build_baseline_rows,
    velocities_from_content_items,
)
from app.repositories.metrics import MetricsRepository
from app.services.scoring_config import ScoringConfig, get_scoring_config


class BaselineService:
    def __init__(
        self,
        session: AsyncSession,
        config: ScoringConfig | None = None,
    ) -> None:
        self._session = session
        self._metrics = MetricsRepository(session)
        self._baselines = BaselinesRepository(session)
        self._config = config or get_scoring_config()

    def _content_to_video_input(
        self, item, *, views: int, tier: str = "general"
    ) -> VideoMetricsInput:
        return VideoMetricsInput(
            content_item_id=str(item.id),
            channel_external_id=item.channel_external_id or "",
            channel_name=item.channel_name or "",
            title=item.title_original,
            published_at=item.published_at,
            views=views,
            likes=None,
            comments=None,
            duration_seconds=item.duration_seconds or 0,
            tier=tier,  # type: ignore[arg-type]
            url=item.url or "",
        )

    async def refresh_channel_baselines(self) -> dict[str, Any]:
        items = await self._metrics.list_content_for_baseline(
            lookback_days=self._config.snapshots.lookback_days,
        )
        now = datetime.now(UTC)
        grouped = velocities_from_content_items(items, now=now, config=self._config)
        rows = build_baseline_rows(grouped, config=self._config)
        upserted = 0
        for row in rows:
            await self._baselines.upsert_baseline(
                channel_external_id=row["channel_external_id"],
                platform=Platform.YOUTUBE,
                age_bucket=row["age_bucket"],
                sample_count=row["sample_count"],
                median_velocity=row["median_velocity"],
                p25_velocity=row["p25_velocity"],
                p75_velocity=row["p75_velocity"],
                confidence=row["confidence"],
                calculated_at=now,
            )
            upserted += 1

        return {
            "channels_processed": len({r["channel_external_id"] for r in rows}),
            "rows_upserted": upserted,
        }

    async def compute_breakout_for_content(
        self,
        item,
        *,
        views: int,
        tier: str = "general",
        now: datetime | None = None,
    ) -> dict[str, Any]:

        now = now or datetime.now(UTC)
        items = await self._metrics.list_content_for_baseline(
            lookback_days=self._config.snapshots.lookback_days,
        )
        video_inputs = [
            self._content_to_video_input(
                row,
                views=self._latest_views(row),
                tier=tier,
            )
            for row in items
            if row.channel_external_id and row.published_at
        ]
        baselines = compute_channel_baselines(video_inputs, now=now, config=self._config)
        global_fallback = global_baseline_by_bucket(video_inputs, now=now)
        target = self._content_to_video_input(item, views=views, tier=tier)
        return breakout_ratio(target, baselines, global_fallback, now=now, config=self._config)

    @staticmethod
    def _latest_views(item) -> int:
        if item.metric_snapshots:
            latest = max(item.metric_snapshots, key=lambda s: s.captured_at)
            return int(latest.views)
        stats = (item.raw_payload or {}).get("statistics", {})
        try:
            return int(stats.get("viewCount", 0))
        except (TypeError, ValueError):
            return 0

    async def load_baseline_map(self) -> tuple[dict, dict]:
        """Return (channel_baselines, global_fallback) for scoring."""
        items = await self._metrics.list_content_for_baseline(
            lookback_days=self._config.snapshots.lookback_days,
        )
        now = datetime.now(UTC)
        video_inputs = [
            self._content_to_video_input(row, views=self._latest_views(row))
            for row in items
            if row.channel_external_id and row.published_at
        ]
        channel_baselines = compute_channel_baselines(video_inputs, now=now, config=self._config)
        global_fallback = global_baseline_by_bucket(video_inputs, now=now)
        return channel_baselines, global_fallback
