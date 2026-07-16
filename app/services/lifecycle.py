"""Trend lifecycle state transitions."""

from __future__ import annotations

from datetime import UTC, datetime

from app.domain.trend_metrics import cluster_activity, compute_growth_ratio
from app.models import LifecycleStatus
from app.repositories.trends import TrendsRepository
from app.services.scoring_config import ScoringConfig, get_scoring_config


def determine_lifecycle_status(
    *,
    first_detected_at: datetime,
    previous_status: LifecycleStatus | None,
    growth_ratio: float,
    activity_last_24h: float,
    latest_video_age_hours: float,
    config: ScoringConfig | None = None,
) -> LifecycleStatus:
    cfg = config or get_scoring_config()
    now = datetime.now(UTC)
    trend_age_hours = (now - first_detected_at).total_seconds() / 3600.0

    if activity_last_24h < cfg.lifecycle.dormant_activity_threshold and latest_video_age_hours > cfg.thresholds.dormant_hours_no_video:
        return LifecycleStatus.DORMANT

    if trend_age_hours <= cfg.lifecycle.new_max_age_hours and previous_status in {None, LifecycleStatus.NEW}:
        return LifecycleStatus.NEW

    if previous_status in {LifecycleStatus.DECLINING, LifecycleStatus.DORMANT} and growth_ratio >= cfg.thresholds.reviving_ratio:
        return LifecycleStatus.REVIVING

    if growth_ratio >= cfg.thresholds.rising_ratio:
        return LifecycleStatus.RISING

    if growth_ratio < cfg.thresholds.declining_ratio:
        return LifecycleStatus.DECLINING

    return LifecycleStatus.STABLE


class LifecycleService:
    def __init__(self, trends_repo: TrendsRepository, config: ScoringConfig | None = None) -> None:
        self._trends = trends_repo
        self._config = config or get_scoring_config()

    async def resolve_status(
        self,
        *,
        trend,
        members: list[dict],
        snapshot_date,
    ) -> LifecycleStatus:
        activity_last = cluster_activity(members, config=self._config)

        previous_snapshot = await self._trends.get_previous_score_snapshot(trend.id, snapshot_date)
        activity_prev = 0.0
        if previous_snapshot and previous_snapshot.score_components:
            activity_prev = float(previous_snapshot.score_components.get("activity_24h", 0.0))

        growth_ratio = compute_growth_ratio(activity_last, activity_prev, config=self._config)

        latest_age = 9999.0
        now = datetime.now(UTC)
        for member in members:
            published = member.get("published_at")
            if published is None:
                continue
            if isinstance(published, str):
                from app.domain.trend_metrics import parse_iso_datetime, video_age_hours

                published = parse_iso_datetime(published)
            latest_age = min(latest_age, video_age_hours(published, now))

        return determine_lifecycle_status(
            first_detected_at=trend.first_detected_at,
            previous_status=trend.lifecycle_status,
            growth_ratio=growth_ratio,
            activity_last_24h=activity_last,
            latest_video_age_hours=latest_age,
            config=self._config,
        )
