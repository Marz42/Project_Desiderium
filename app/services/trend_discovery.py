"""Orchestrate baseline refresh, clustering, scoring, and daily snapshots."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.trend_metrics import VideoMetricsInput, breakout_ratio, cluster_activity
from app.models import (
    ClusterDecisionAction,
    ContentItem,
    LifecycleStatus,
    MembershipMethod,
    Platform,
    WatchItem,
    WatchTier,
)
from app.repositories.analysis_runs import AnalysisRunRepository
from app.repositories.trends import TrendsRepository
from app.services.baseline import BaselineService
from app.services.clustering import (
    assignments_to_member_rows,
    cluster_videos,
    topic_type_from_string,
)
from app.services.lifecycle import LifecycleService
from app.services.relevance import classify_relevance
from app.services.run_metadata import (
    algorithm_version,
    config_hash,
    load_config_snapshot,
    run_fingerprint,
)
from app.services.scoring import TrendScoringService
from app.services.scoring_config import DEFAULT_ENTITIES_PATH, get_scoring_config
from app.services.trend_consistency import TrendConsistencyService

logger = logging.getLogger(__name__)


class TrendDiscoveryService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._config = get_scoring_config()
        self._baseline = BaselineService(session, self._config)
        self._trends = TrendsRepository(session)
        self._scoring = TrendScoringService(self._config)
        self._lifecycle = LifecycleService(self._trends, self._config)
        self._runs = AnalysisRunRepository(session)
        self._consistency = TrendConsistencyService(session, config=self._config.clustering)

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

    @staticmethod
    def _entity_dictionary_hash(path: Path = DEFAULT_ENTITIES_PATH) -> str:
        return config_hash({"entities_text": path.read_text(encoding="utf-8")})

    async def run_daily_pipeline(
        self,
        *,
        snapshot_date: date | None = None,
        analysis_run_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        snapshot_date = snapshot_date or datetime.now(UTC).date()
        now = datetime.now(UTC)
        scoring_snapshot = load_config_snapshot()
        algorithm = algorithm_version()
        snapshot_hash = config_hash(scoring_snapshot)
        run = await self._runs.start(
            run_date=snapshot_date,
            run_kind="trend_discovery",
            scoring_version=str(scoring_snapshot.get("version")),
            algorithm_version=algorithm,
            config_hash=snapshot_hash,
            run_fingerprint=run_fingerprint(
                run_date=snapshot_date,
                run_kind="trend_discovery",
                config_hash_value=snapshot_hash,
                algorithm_version_value=algorithm,
            ),
            config_snapshot={
                **scoring_snapshot,
                "entity_dictionary_hash": self._entity_dictionary_hash(),
            },
            prompt_versions={},
            analysis_run_id=analysis_run_id,
        )

        baseline_summary = await self._baseline.refresh_channel_baselines()
        channel_baselines, global_fallback = await self._baseline.load_baseline_map()
        tier_map = await self._channel_tier_map()
        items = await self._load_scoring_candidates()

        video_rows: list[dict[str, Any]] = []
        for item in items:
            if not item.channel_external_id or not item.published_at:
                continue
            relevance = classify_relevance(
                title=item.title_original,
                language=item.language,
                config=self._config.relevance,
            )
            if relevance.multiplier <= 0:
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
                    "language": item.language,
                    "relevance_category": relevance.category,
                    "relevance_multiplier": relevance.multiplier,
                    **breakout,
                }
            )

        clusters = cluster_videos(video_rows)
        video_lookup = {row["content_item_id"]: row for row in video_rows}
        trends_upserted = 0
        snapshots_written = 0
        skipped_threshold = 0
        merges = 0
        needs_review = 0

        for entity_id, assignments in clusters.items():
            member_dicts = assignments_to_member_rows(assignments, video_lookup)
            score = self._scoring.score_cluster(member_dicts)
            if not score.get("meets_standard_threshold") and not score.get("meets_early_signal"):
                skipped_threshold += 1
                continue

            first_assignment = assignments[0]
            source_meta = {
                "entity_id": entity_id,
                "anime_title": first_assignment.anime_title,
                "topic_type": first_assignment.topic_type,
                "language": next(
                    (m.get("language") for m in member_dicts if m.get("language")),
                    "en",
                ),
                "published_at": next(
                    (m.get("published_at") for m in member_dicts if m.get("published_at")),
                    now,
                ),
            }
            decision = await self._consistency.decide_target_trend(
                source_cluster_key=entity_id,
                source_meta=source_meta,
                members=member_dicts,
            )
            await self._consistency.record_decision(
                source_cluster_key=entity_id,
                decision=decision,
                evidence={
                    "member_count": len(member_dicts),
                    "analysis_run_id": str(run.id),
                    "retriever_mode": (
                        "lexical"
                        if decision.degraded or decision.source.value == "lexical"
                        else "embedding"
                    ),
                    "degraded": decision.degraded,
                    "thresholds": {
                        "high_similarity": self._config.clustering.high_similarity,
                        "low_similarity": self._config.clustering.low_similarity,
                        "llm_min_confidence": self._config.clustering.llm_min_confidence,
                    },
                },
            )
            if decision.action == ClusterDecisionAction.NEEDS_REVIEW:
                needs_review += 1

            existing = None
            if decision.target_trend_id is not None and decision.action in {
                ClusterDecisionAction.MERGE_SAME_ANGLE,
                ClusterDecisionAction.MERGE_THEME_KEEP_ANGLES_SEPARATE,
            }:
                existing = await self._trends.get_by_id(decision.target_trend_id)
                merges += 1
            if existing is None:
                existing = await self._trends.get_by_entity_id(entity_id)

            topic_type = topic_type_from_string(first_assignment.topic_type)
            entities_payload = {
                "entity_id": entity_id,
                "anime_title": first_assignment.anime_title,
                "keywords_matched": [
                    kw for a in assignments for kw in a.evidence.get("keywords_matched", [])
                ],
                "merge_decision": decision.action.value,
            }
            activity_24h = cluster_activity(member_dicts, now=now, config=self._config)
            membership_scores = [float(a.membership_score) for a in assignments]
            clustering_confidence = (
                float(decision.confidence)
                if decision.confidence is not None
                else (sum(membership_scores) / len(membership_scores) if membership_scores else 0.0)
            )

            trend = await self._trends.upsert_trend(
                entity_id=entity_id
                if existing is None
                else str(
                    (existing.entities or {}).get("entity_id") or entity_id,
                ),
                canonical_name=(
                    existing.canonical_name
                    if existing is not None
                    else first_assignment.canonical_name
                ),
                anime_title=(
                    existing.anime_title
                    if existing is not None
                    else (first_assignment.anime_title or None)
                ),
                topic_type=topic_type if existing is None else existing.topic_type,
                entities=entities_payload
                if existing is None
                else {
                    **(existing.entities or {}),
                    **entities_payload,
                },
                score=float(score["trend_score"]),
                score_components={
                    **score,
                    "activity_24h": activity_24h,
                    "clustering_confidence": clustering_confidence,
                },
                confidence=clustering_confidence,
                lifecycle_status=existing.lifecycle_status if existing else LifecycleStatus.NEW,
                now=now,
                existing=existing,
            )

            if (
                decision.action == ClusterDecisionAction.MERGE_THEME_KEEP_ANGLES_SEPARATE
                and decision.facet_label
            ):
                await self._consistency.ensure_facet(
                    trend.id,
                    label=decision.facet_label,
                    evidence={"source_cluster_key": entity_id},
                )

            membership_method = (
                MembershipMethod.EMBEDDING
                if decision.source.value in {"auto_high", "llm"}
                else MembershipMethod.RULE
            )
            await self._trends.sync_members(
                trend.id,
                [
                    {
                        "content_item_id": uuid.UUID(m["content_item_id"]),
                        "membership_score": m.get("membership_score"),
                        "evidence": m.get("evidence"),
                        "membership_method": membership_method,
                    }
                    for m in member_dicts
                ],
                now=now,
                membership_method=membership_method,
            )

            lifecycle_status = await self._lifecycle.resolve_status(
                trend=trend,
                members=member_dicts,
                snapshot_date=snapshot_date,
            )
            trend.lifecycle_status = lifecycle_status
            trend.score = float(score["trend_score"])
            trend.score_components = {
                **score,
                "activity_24h": activity_24h,
                "clustering_confidence": clustering_confidence,
            }
            trend.confidence = clustering_confidence
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

        summary = {
            "snapshot_date": snapshot_date.isoformat(),
            "baseline": baseline_summary,
            "videos_scored": len(video_rows),
            "clusters_found": len(clusters),
            "trends_upserted": trends_upserted,
            "skipped_threshold": skipped_threshold,
            "merges": merges,
            "needs_review": needs_review,
            "score_snapshots_written": snapshots_written,
            "analysis_run_id": str(run.id),
        }
        await self._runs.finish(run, summary)
        await self._consistency.close()
        await self._session.commit()
        return summary
