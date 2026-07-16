from __future__ import annotations

import statistics
import uuid
from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.trend_metrics import (
    AgeBucketKey,
    age_bucket_key_to_model,
    baseline_confidence_label,
    cold_start_velocity,
    video_age_hours,
)
from app.models import AgeBucket, BaselineConfidence, ChannelBaseline, Platform
from app.services.scoring_config import ScoringConfig, get_scoring_config


class BaselinesRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_baseline(
        self,
        *,
        channel_external_id: str,
        platform: Platform,
        age_bucket: AgeBucket,
        sample_count: int,
        median_velocity: float,
        p25_velocity: float | None,
        p75_velocity: float | None,
        confidence: BaselineConfidence,
        calculated_at: datetime | None = None,
    ) -> ChannelBaseline:
        calculated_at = calculated_at or datetime.now(UTC)
        values = {
            "channel_external_id": channel_external_id,
            "platform": platform,
            "age_bucket": age_bucket,
            "sample_count": sample_count,
            "median_velocity": median_velocity,
            "p25_velocity": p25_velocity,
            "p75_velocity": p75_velocity,
            "calculated_at": calculated_at,
            "confidence": confidence,
        }
        stmt = (
            insert(ChannelBaseline)
            .values(id=uuid.uuid4(), **values)
            .on_conflict_do_update(
                index_elements=["channel_external_id", "platform", "age_bucket"],
                set_={
                    "sample_count": values["sample_count"],
                    "median_velocity": values["median_velocity"],
                    "p25_velocity": values["p25_velocity"],
                    "p75_velocity": values["p75_velocity"],
                    "calculated_at": values["calculated_at"],
                    "confidence": values["confidence"],
                },
            )
            .returning(ChannelBaseline.id)
        )
        result = await self._session.execute(stmt)
        row_id = result.scalar_one()
        row = await self._session.get(ChannelBaseline, row_id)
        assert row is not None
        return row

    async def list_all(self, platform: Platform = Platform.YOUTUBE) -> list[ChannelBaseline]:
        from sqlalchemy import select

        stmt = select(ChannelBaseline).where(ChannelBaseline.platform == platform)
        result = await self._session.scalars(stmt)
        return list(result.all())


def build_baseline_rows(
    grouped_velocities: dict[tuple[str, AgeBucketKey], list[float]],
    *,
    config: ScoringConfig | None = None,
) -> list[dict]:
    cfg = config or get_scoring_config()
    rows: list[dict] = []
    for (channel_id, bucket_key), velocities in grouped_velocities.items():
        model_bucket = age_bucket_key_to_model(bucket_key)
        if model_bucket is None:
            continue
        sample = velocities[-cfg.baselines.sample_size :]
        count = len(sample)
        if count == 0:
            continue
        _, confidence = baseline_confidence_label(count, config=cfg)
        rows.append(
            {
                "channel_external_id": channel_id,
                "age_bucket": model_bucket,
                "sample_count": count,
                "median_velocity": statistics.median(sample),
                "p25_velocity": statistics.quantiles(sample, n=4)[0] if count >= 4 else None,
                "p75_velocity": statistics.quantiles(sample, n=4)[2] if count >= 4 else None,
                "confidence": confidence,
            }
        )
    return rows


def velocities_from_content_items(
    items: list,
    *,
    now: datetime | None = None,
    config: ScoringConfig | None = None,
) -> dict[tuple[str, AgeBucketKey], list[float]]:
    from app.domain.trend_metrics import assign_age_bucket

    cfg = config or get_scoring_config()
    now = now or datetime.now(UTC)
    grouped: dict[tuple[str, AgeBucketKey], list[float]] = {}

    for item in items:
        if not item.published_at or not item.channel_external_id:
            continue
        age = video_age_hours(item.published_at, now)
        bucket = assign_age_bucket(age)
        if bucket == "7d_plus":
            continue
        views = 0
        if item.metric_snapshots:
            latest = max(item.metric_snapshots, key=lambda s: s.captured_at)
            views = int(latest.views)
        elif item.raw_payload:
            stats = (item.raw_payload or {}).get("statistics", {})
            try:
                views = int(stats.get("viewCount", 0))
            except (TypeError, ValueError):
                views = 0
        velocity = cold_start_velocity(views, age, config=cfg)
        grouped.setdefault((item.channel_external_id, bucket), []).append(velocity)

    return grouped
