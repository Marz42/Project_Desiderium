"""Orchestrate baseline refresh, clustering, scoring, and daily snapshots."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.trend_metrics import VideoMetricsInput, breakout_ratio
from app.models import ContentItem, LifecycleStatus, Platform, WatchItem, WatchTier
from app.repositories.trends import TrendsRepository
from app.services.baseline import BaselineService
from app.services.clustering import (
    assignments_to_member_rows,
    cluster_videos,
    topic_type_from_string,
)
from app.services.lifecycle import LifecycleService
from app.services.scoring import TrendScoringService
from app.services.scoring_config import get_scoring_config

logger = logging.getLogger(__name__)


class TrendDiscoveryService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._config = get_scoring_config()
        self._baseline = BaselineService(session, self._config)
        self._trends = TrendsRepository(session)
        self._scoring = TrendScoringService(self._config)
        self._lifecycle = LifecycleService(self._trends, self._config)

    async def _channel_tier_map(self) -> dict[str, str]:
        stmt = select(WatchItem).where(
            WatchItem.platform == Platform.YOUTUBE,
            WatchItem.enabled.is_(True),
        )
        items = list((await self._session.scalars(stmt)).all())
        tiers: dict[str, str] = {}
        for item in items:
            if item.type.value not in {"channel", "account"}:
                continue
            tiers[item.external_id] = item.tier.value
        return tiers

    async def _load_scoring_candidates(self) -> list[ContentItem]:
        cutoff = datetime.now(UTC) - timedelta(days=self._config.snapshots.lookback_days)
        stmt = (
            select(ContentItem)
            .options(selectinload(ContentItem.metric_snapshots))
            .where(
                ContentItem.platform == Platform.YOUTUBE,
                ContentItem.published_at.is_not(None),
                ContentItem.published_at >= cutoff,
            )
        )
        return list((await self._session.scalars(stmt)).all())

    @staticmethod
    def _incremental_views(item: ContentItem) -> int:
        if not item.metric_snapshots:
            return 0
        ordered = sorted(item.metric_snapshots, key=lambda s: s.captured_at, reverse=True)
        if len(ordered) < 2:
            return 0
        return max(int(ordered[0].views) - int(ordered[1].views), 0)

    async def run_daily_pipeline(self, *, snapshot_date: date | None = None) -> dict[str, Any]:
        snapshot_date = snapshot_date or datetime.now(UTC).date()
        now = datetime.now(UTC)

        baseline_summary = await self._baseline.refresh_channel_baselines()
        channel_baselines, global_fallback = await self._baseline.load_baseline_map()
        tier_map = await self._channel_tier_map()
        items = await self._load_scoring_candidates()

        video_rows: list[dict[str, Any]] = []
        for item in items:
            if not item.channel_external_id or not item.published_at:
                continue
            views = BaselineService._latest_views(item)
            tier = tier_map.get(item.channel_external_id, WatchTier.GENERAL.value)
            video_input = VideoMetricsInput(
                content_item_id=str(item.id),
                channel_external_id=item.channel_external_id,
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
            breakout = breakout_ratio(
                video_input,
                channel_baselines,
                global_fallback,
                now=now,
                config=self._config,
            )
            video_rows.append(
                {
                    "content_item_id": str(item.id),
                    "channel_id": item.channel_external_id,
                    "channel_external_id": item.channel_external_id,
                    "title": item.title_original,
                    "title_original": item.title_original,
                    "tier": tier,
                    "views": views,
                    "incremental_views": self._incremental_views(item),
                    "published_at": item.published_at,
                    **breakout,
                }
            )

        clusters = cluster_videos(video_rows)
        video_lookup = {row["content_item_id"]: row for row in video_rows}
        trends_upserted = 0
        snapshots_written = 0

        for entity_id, assignments in clusters.items():
            member_dicts = assignments_to_member_rows(assignments, video_lookup)
            score = self._scoring.score_cluster(member_dicts)
            if not score.get("meets_standard_threshold") and not score.get("meets_early_signal"):
                if int(score.get("channel_count", 0)) < self._config.thresholds.min_cluster_channels:
                    continue

            first_assignment = assignments[0]
            existing = await self._trends.get_by_entity_id(entity_id)
            topic_type = topic_type_from_string(first_assignment.topic_type)
            entities_payload = {
                "entity_id": entity_id,
                "anime_title": first_assignment.anime_title,
                "keywords_matched": [
                    kw for a in assignments for kw in a.evidence.get("keywords_matched", [])
                ],
            }

            trend = await self._trends.upsert_trend(
                entity_id=entity_id,
                canonical_name=first_assignment.canonical_name,
                anime_title=first_assignment.anime_title or None,
                topic_type=topic_type,
                entities=entities_payload,
                score=float(score["trend_score"]),
                score_components={
                    **score,
                    "activity_24h": score.get("momentum", 0),
                },
                confidence=float(score.get("channel_resonance", 0)) / 100.0,
                lifecycle_status=existing.lifecycle_status if existing else LifecycleStatus.NEW,
                now=now,
                existing=existing,
            )

            await self._trends.replace_members(
                trend.id,
                [
                    {
                        "content_item_id": uuid.UUID(m["content_item_id"]),
                        "membership_score": m.get("membership_score"),
                        "evidence": m.get("evidence"),
                    }
                    for m in member_dicts
                ],
            )

            lifecycle_status = await self._lifecycle.resolve_status(
                trend=trend,
                members=member_dicts,
                snapshot_date=snapshot_date,
            )
            trend.lifecycle_status = lifecycle_status
            trend.score = float(score["trend_score"])
            trend.score_components = {**score, "activity_24h": score.get("momentum", 0)}
            trend.last_active_at = now

            await self._trends.upsert_score_snapshot(
                trend_id=trend.id,
                snapshot_date=snapshot_date,
                score=float(score["trend_score"]),
                score_components=trend.score_components or {},
                lifecycle_status=lifecycle_status,
                member_count=len(member_dicts),
                channel_count=int(score.get("channel_count", 0)),
            )
            trends_upserted += 1
            snapshots_written += 1

        await self._session.commit()
        return {
            "snapshot_date": snapshot_date.isoformat(),
            "baseline": baseline_summary,
            "videos_scored": len(video_rows),
            "clusters_found": len(clusters),
            "trends_upserted": trends_upserted,
            "score_snapshots_written": snapshots_written,
        }
