"""Bounded embedding recall and gray-zone adjudication for trend themes."""

from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.embedding.base import EmbeddingProvider
from app.adapters.embedding.factory import create_embedding_provider
from app.adapters.llm.adapter import LlmAdapter, LlmAdapterError
from app.domain.cluster_constraints import cosine_similarity, hard_constraints_allow_merge
from app.models import (
    BriefItem,
    ClusterDecisionAction,
    ClusterDecisionAudit,
    ClusterDecisionSource,
    CreativeAngle,
    DailyCandidate,
    EmbeddingCache,
    MembershipMethod,
    PublicationRecord,
    TrendFacet,
    TrendMember,
    TrendTheme,
)
from app.schemas.semantic import ClusterAdjudicationResult
from app.services.llm_config import load_prompt_template
from app.services.scoring_config import ClusteringConfig, get_scoring_config

logger = logging.getLogger(__name__)


class RollbackConflict(RuntimeError):
    """Raised when a later decision makes an older rollback unsafe."""


@dataclass(frozen=True)
class MergeDecision:
    action: ClusterDecisionAction
    target_trend_id: uuid.UUID | None
    similarity: float | None
    confidence: float | None
    source: ClusterDecisionSource
    reason: str
    facet_label: str | None = None
    embedding_space: str | None = None
    degraded: bool = False
    candidate_evidence: dict[str, Any] = field(default_factory=dict)


def _input_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _member_snapshot(member: TrendMember) -> dict[str, Any]:
    return {
        "member_id": str(member.id),
        "content_item_id": str(member.content_item_id),
        "trend_id": str(member.trend_id),
        "active": member.active,
        "membership_method": member.membership_method.value,
        "membership_score": member.membership_score,
        "evidence": member.evidence,
        "last_confirmed_at": (
            member.last_confirmed_at.isoformat() if member.last_confirmed_at else None
        ),
        "deactivated_at": member.deactivated_at.isoformat() if member.deactivated_at else None,
        "decision_version": member.decision_version,
    }


def _parse_optional_datetime(value: Any) -> datetime | None:
    return datetime.fromisoformat(value) if isinstance(value, str) and value else None


def build_cluster_text(members: list[dict[str, Any]], *, anime_title: str, entity_id: str) -> str:
    titles = [str(m.get("title") or "") for m in members[:8]]
    return " | ".join(
        [
            f"anime:{anime_title}",
            f"entity:{entity_id}",
            *titles,
        ],
    )


class TrendConsistencyService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        embedding: EmbeddingProvider | None = None,
        llm: LlmAdapter | None = None,
        config: ClusteringConfig | None = None,
    ) -> None:
        self._session = session
        self._config = config or get_scoring_config().clustering
        self._embedding = embedding or create_embedding_provider(self._config)
        self._llm = llm

    async def close(self) -> None:
        await self._embedding.close()

    async def decide_target_trend(
        self,
        *,
        source_cluster_key: str,
        source_meta: dict[str, Any],
        members: list[dict[str, Any]],
    ) -> MergeDecision:
        if not self._config.enabled:
            return MergeDecision(
                action=ClusterDecisionAction.CREATE_NEW_THEME,
                target_trend_id=None,
                similarity=None,
                confidence=1.0,
                source=ClusterDecisionSource.AUTO_LOW,
                reason="clustering_disabled",
            )

        text = build_cluster_text(
            members,
            anime_title=str(source_meta.get("anime_title") or ""),
            entity_id=source_cluster_key,
        )
        embedded = await self._embed_cached(text)
        if embedded.degraded and embedded.provider == "lexical":
            # Lexical degradation never auto-merges gray/high without exact entity match.
            existing = await self._session.scalar(
                select(TrendTheme).where(
                    TrendTheme.entities["entity_id"].astext == source_cluster_key,
                    TrendTheme.active.is_(True),
                ),
            )
            if existing is not None:
                return MergeDecision(
                    action=ClusterDecisionAction.MERGE_SAME_ANGLE,
                    target_trend_id=existing.id,
                    similarity=1.0,
                    confidence=0.99,
                    source=ClusterDecisionSource.LEXICAL,
                    reason="entity_id_exact_match_degraded_embedding",
                    embedding_space=embedded.embedding_space,
                    degraded=True,
                )
            return MergeDecision(
                action=ClusterDecisionAction.CREATE_NEW_THEME,
                target_trend_id=None,
                similarity=None,
                confidence=0.5,
                source=ClusterDecisionSource.LEXICAL,
                reason=embedded.degradation_reason or "embedding_degraded_to_lexical",
                embedding_space=embedded.embedding_space,
                degraded=True,
            )

        candidates = await self._recall_candidates(source_meta, embedded.vector)
        if not candidates:
            return MergeDecision(
                action=ClusterDecisionAction.CREATE_NEW_THEME,
                target_trend_id=None,
                similarity=None,
                confidence=1.0,
                source=ClusterDecisionSource.AUTO_LOW,
                reason="no_compatible_candidates",
                embedding_space=embedded.embedding_space,
                degraded=embedded.degraded,
            )

        best_trend, best_sim, best_payload = candidates[0]
        candidate_evidence = {
            "top_k_candidate_trends": [str(trend.id) for trend, _, _ in candidates],
            "similarity_scores": [round(similarity, 6) for _, similarity, _ in candidates],
            "entity_constraints": "hard_constraints_passed",
        }
        if best_sim >= self._config.high_similarity:
            return MergeDecision(
                action=ClusterDecisionAction.MERGE_SAME_ANGLE,
                target_trend_id=best_trend.id,
                similarity=best_sim,
                confidence=best_sim,
                source=ClusterDecisionSource.AUTO_HIGH,
                reason="high_similarity_auto_merge",
                embedding_space=embedded.embedding_space,
                degraded=embedded.degraded,
                candidate_evidence=candidate_evidence,
            )
        if best_sim < self._config.low_similarity:
            return MergeDecision(
                action=ClusterDecisionAction.CREATE_NEW_THEME,
                target_trend_id=None,
                similarity=best_sim,
                confidence=1.0 - best_sim,
                source=ClusterDecisionSource.AUTO_LOW,
                reason="below_low_similarity",
                embedding_space=embedded.embedding_space,
                degraded=embedded.degraded,
                candidate_evidence=candidate_evidence,
            )

        return await self._adjudicate_gray_zone(
            source_meta=source_meta,
            members=members,
            candidate=best_trend,
            candidate_payload=best_payload,
            similarity=best_sim,
            embedding_space=embedded.embedding_space,
            degraded=embedded.degraded,
            candidate_evidence=candidate_evidence,
        )

    async def record_decision(
        self,
        *,
        source_cluster_key: str,
        decision: MergeDecision,
        evidence: dict[str, Any] | None = None,
    ) -> ClusterDecisionAudit:
        merged_evidence = {
            **decision.candidate_evidence,
            **(evidence or {}),
        }
        row = ClusterDecisionAudit(
            source_cluster_key=source_cluster_key,
            target_trend_id=decision.target_trend_id,
            action=decision.action,
            source=decision.source,
            similarity=decision.similarity,
            confidence=decision.confidence,
            embedding_space=decision.embedding_space,
            reason=decision.reason,
            evidence=merged_evidence or None,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def ensure_facet(
        self,
        trend_id: uuid.UUID,
        *,
        label: str,
        evidence: dict[str, Any] | None = None,
    ) -> TrendFacet:
        key = hashlib.sha256(label.strip().lower().encode("utf-8")).hexdigest()[:24]
        existing = await self._session.scalar(
            select(TrendFacet).where(
                TrendFacet.trend_id == trend_id,
                TrendFacet.facet_key == key,
            ),
        )
        if existing is not None:
            return existing
        facet = TrendFacet(
            trend_id=trend_id,
            facet_key=key,
            label=label.strip(),
            evidence=evidence,
        )
        self._session.add(facet)
        await self._session.flush()
        return facet

    async def manual_merge(
        self,
        *,
        source_trend_id: uuid.UUID,
        target_trend_id: uuid.UUID,
        note: str | None = None,
    ) -> ClusterDecisionAudit:
        if source_trend_id == target_trend_id:
            raise ValueError("source and target trends must differ")
        source = await self._session.scalar(
            select(TrendTheme).where(TrendTheme.id == source_trend_id).with_for_update(),
        )
        target = await self._session.scalar(
            select(TrendTheme).where(TrendTheme.id == target_trend_id).with_for_update(),
        )
        if source is None or target is None:
            raise ValueError("trend not found")
        if await self._trend_is_protected(source.id) or await self._trend_is_protected(target.id):
            # Still allow manual merge, but record protection note.
            note = (note or "") + " | protected_history_manual_override"

        members = list(
            (
                await self._session.scalars(
                    select(TrendMember).where(
                        TrendMember.trend_id == source.id,
                        TrendMember.active.is_(True),
                    ).with_for_update(),
                )
            ).all(),
        )
        source_previous_state = {
            "active": source.active,
            "lifecycle_status": source.lifecycle_status.value,
            "merged_into_id": str(source.merged_into_id) if source.merged_into_id else None,
        }
        affected_members: list[dict[str, Any]] = []
        for member in members:
            conflict = await self._session.scalar(
                select(TrendMember).where(
                    TrendMember.trend_id == target.id,
                    TrendMember.content_item_id == member.content_item_id,
                ).with_for_update(),
            )
            source_snapshot = _member_snapshot(member)
            if conflict is not None:
                conflict_snapshot = _member_snapshot(conflict)
                conflict.active = True
                conflict.last_confirmed_at = datetime.now(UTC)
                conflict.deactivated_at = None
                conflict.membership_method = MembershipMethod.MANUAL
                conflict.decision_version += 1
                member.active = False
                member.deactivated_at = datetime.now(UTC)
                member.membership_method = MembershipMethod.MANUAL
                member.decision_version += 1
                source_snapshot["applied_version"] = member.decision_version
                conflict_snapshot["applied_version"] = conflict.decision_version
                affected_members.extend([source_snapshot, conflict_snapshot])
            else:
                member.trend_id = target.id
                member.membership_method = MembershipMethod.MANUAL
                member.last_confirmed_at = datetime.now(UTC)
                member.deactivated_at = None
                member.active = True
                member.decision_version += 1
                source_snapshot["applied_version"] = member.decision_version
                affected_members.append(source_snapshot)

        source.active = False
        source.merged_into_id = target.id

        decision = MergeDecision(
            action=ClusterDecisionAction.MANUAL_MERGE,
            target_trend_id=target.id,
            similarity=None,
            confidence=1.0,
            source=ClusterDecisionSource.MANUAL,
            reason=note or "manual_merge",
        )
        return await self.record_decision(
            source_cluster_key=str(
                source.entities.get("entity_id") if source.entities else source.id
            ),
            decision=decision,
            evidence={
                "source_trend_id": str(source.id),
                "target_trend_id": str(target.id),
                "affected_members": affected_members,
                "source_trend_previous_state": source_previous_state,
            },
        )

    async def manual_move_out(
        self,
        *,
        trend_id: uuid.UUID,
        content_item_id: uuid.UUID,
        note: str | None = None,
    ) -> ClusterDecisionAudit:
        member = await self._session.scalar(
            select(TrendMember).where(
                TrendMember.trend_id == trend_id,
                TrendMember.content_item_id == content_item_id,
            ).with_for_update(),
        )
        if member is None:
            raise ValueError("membership not found")
        previous_state = _member_snapshot(member)
        member.active = False
        member.deactivated_at = datetime.now(UTC)
        member.membership_method = MembershipMethod.MANUAL
        member.decision_version += 1
        previous_state["applied_version"] = member.decision_version
        decision = MergeDecision(
            action=ClusterDecisionAction.MANUAL_MOVE_OUT,
            target_trend_id=trend_id,
            similarity=None,
            confidence=1.0,
            source=ClusterDecisionSource.MANUAL,
            reason=note or "manual_move_out",
        )
        return await self.record_decision(
            source_cluster_key=str(content_item_id),
            decision=decision,
            evidence={
                "content_item_id": str(content_item_id),
                "trend_id": str(trend_id),
                "affected_members": [previous_state],
            },
        )

    async def manual_restore_member(
        self,
        *,
        trend_id: uuid.UUID,
        content_item_id: uuid.UUID,
        note: str | None = None,
    ) -> ClusterDecisionAudit:
        member = await self._session.scalar(
            select(TrendMember)
            .where(
                TrendMember.trend_id == trend_id,
                TrendMember.content_item_id == content_item_id,
            )
            .with_for_update(),
        )
        if member is None:
            raise ValueError("membership not found")
        member.active = True
        member.deactivated_at = None
        member.last_confirmed_at = datetime.now(UTC)
        member.membership_method = MembershipMethod.MANUAL
        member.decision_version += 1
        decision = MergeDecision(
            action=ClusterDecisionAction.MERGE_SAME_ANGLE,
            target_trend_id=trend_id,
            similarity=None,
            confidence=1.0,
            source=ClusterDecisionSource.MANUAL,
            reason=note or "manual_restore_member",
        )
        return await self.record_decision(
            source_cluster_key=str(content_item_id),
            decision=decision,
            evidence={
                "content_item_id": str(content_item_id),
                "trend_id": str(trend_id),
                "manual_restore": True,
                "decision_version": member.decision_version,
            },
        )

    async def rollback_decision(
        self, audit_id: uuid.UUID, *, note: str | None = None
    ) -> ClusterDecisionAudit:
        async with self._session.begin_nested():
            original = await self._session.scalar(
                select(ClusterDecisionAudit)
                .where(ClusterDecisionAudit.id == audit_id)
                .with_for_update(),
            )
            if original is None:
                raise ValueError("decision not found")
            if original.rolled_back:
                if original.rollback_audit_id is not None:
                    existing = await self._session.get(
                        ClusterDecisionAudit,
                        original.rollback_audit_id,
                    )
                    if existing is not None:
                        return existing
                return original
            if original.action not in {
                ClusterDecisionAction.MANUAL_MERGE,
                ClusterDecisionAction.MANUAL_MOVE_OUT,
            }:
                raise ValueError("only manual merge or move-out decisions can be rolled back")

            evidence = original.evidence or {}
            snapshots = evidence.get("affected_members")
            if not isinstance(snapshots, list):
                raise RollbackConflict("decision has no restorable membership snapshot")

            locked_members: list[tuple[TrendMember, dict[str, Any]]] = []
            for snapshot in snapshots:
                if not isinstance(snapshot, dict):
                    raise RollbackConflict("invalid membership snapshot")
                member_id = uuid.UUID(str(snapshot["member_id"]))
                member = await self._session.scalar(
                    select(TrendMember)
                    .where(TrendMember.id == member_id)
                    .with_for_update(),
                )
                if member is None:
                    raise RollbackConflict(f"membership {member_id} no longer exists")
                if member.decision_version != int(snapshot["applied_version"]):
                    raise RollbackConflict(
                        f"membership {member_id} changed after the original decision",
                    )
                locked_members.append((member, snapshot))

            source_state = evidence.get("source_trend_previous_state")
            source: TrendTheme | None = None
            if isinstance(source_state, dict):
                source_id = uuid.UUID(str(evidence["source_trend_id"]))
                source = await self._session.scalar(
                    select(TrendTheme).where(TrendTheme.id == source_id).with_for_update(),
                )
                if source is None:
                    raise RollbackConflict("source trend no longer exists")

            for member, snapshot in locked_members:
                member.trend_id = uuid.UUID(str(snapshot["trend_id"]))
                member.active = bool(snapshot["active"])
                member.membership_method = MembershipMethod(str(snapshot["membership_method"]))
                member.membership_score = snapshot.get("membership_score")
                member.evidence = snapshot.get("evidence")
                member.last_confirmed_at = _parse_optional_datetime(
                    snapshot.get("last_confirmed_at"),
                ) or member.last_confirmed_at
                member.deactivated_at = _parse_optional_datetime(snapshot.get("deactivated_at"))
                member.decision_version += 1

            if source is not None and isinstance(source_state, dict):
                source.active = bool(source_state["active"])
                source.lifecycle_status = type(source.lifecycle_status)(
                    source_state["lifecycle_status"],
                )
                merged_into_id = source_state.get("merged_into_id")
                source.merged_into_id = uuid.UUID(merged_into_id) if merged_into_id else None

            rolled_back_at = datetime.now(UTC)
            rollback = ClusterDecisionAudit(
                source_cluster_key=original.source_cluster_key,
                target_trend_id=original.target_trend_id,
                action=ClusterDecisionAction.ROLLBACK,
                source=ClusterDecisionSource.MANUAL,
                similarity=original.similarity,
                confidence=1.0,
                embedding_space=original.embedding_space,
                reason=note or f"rollback of {audit_id}",
                evidence={"rollback_of": str(audit_id)},
                rollback_of_id=original.id,
                decision_version=original.decision_version,
            )
            self._session.add(rollback)
            await self._session.flush()
            original.rolled_back = True
            original.rolled_back_at = rolled_back_at
            original.rollback_audit_id = rollback.id
            await self._session.flush()
            return rollback

    async def _embed_cached(self, text: str):
        emb_cfg = self._config.embedding
        digest = _input_hash(text)
        if emb_cfg.cache_enabled:
            cached = await self._session.scalar(
                select(EmbeddingCache).where(
                    EmbeddingCache.embedding_space == emb_cfg.embedding_space,
                    EmbeddingCache.input_hash == digest,
                ),
            )
            if cached is not None:
                from app.adapters.embedding.base import EmbeddingResult

                return EmbeddingResult(
                    vector=[float(x) for x in cached.vector],
                    embedding_space=cached.embedding_space,
                    provider=cached.provider,
                )

        result = await self._embedding.embed(text)
        # Never mix spaces silently.
        if result.embedding_space != emb_cfg.embedding_space and result.provider != "lexical":
            raise RuntimeError(
                f"embedding space mismatch: expected {emb_cfg.embedding_space}, "
                f"got {result.embedding_space}",
            )
        if emb_cfg.cache_enabled and not result.degraded:
            self._session.add(
                EmbeddingCache(
                    embedding_space=result.embedding_space,
                    provider=result.provider,
                    model_name=emb_cfg.model_name,
                    model_revision=emb_cfg.model_revision,
                    input_hash=digest,
                    vector=result.vector,
                ),
            )
            await self._session.flush()
        return result

    async def _recall_candidates(
        self,
        source_meta: dict[str, Any],
        vector: list[float],
    ) -> list[tuple[TrendTheme, float, dict[str, Any]]]:
        trends = list(
            (
                await self._session.scalars(
                    select(TrendTheme)
                    .where(TrendTheme.active.is_(True))
                    .order_by(TrendTheme.last_active_at.desc())
                    .limit(200),
                )
            ).all(),
        )
        scored: list[tuple[TrendTheme, float, dict[str, Any]]] = []
        for trend in trends:
            entities = trend.entities or {}
            payload = {
                "entity_id": entities.get("entity_id"),
                "anime_title": trend.anime_title,
                "topic_type": trend.topic_type.value if trend.topic_type else None,
                "language": "en",
                "published_at": trend.last_active_at,
                "has_brief_or_publication": await self._trend_is_protected(trend.id),
            }
            constraints = hard_constraints_allow_merge(
                source_meta,
                payload,
                max_gap_days=self._config.max_publish_gap_days,
            )
            if not constraints.allowed:
                continue
            text = " | ".join(
                [
                    f"anime:{trend.anime_title or ''}",
                    f"entity:{entities.get('entity_id') or ''}",
                    trend.canonical_name,
                    trend.summary_zh or "",
                ],
            )
            candidate_emb = await self._embed_cached(text)
            if candidate_emb.degraded:
                continue
            if candidate_emb.embedding_space != self._config.embedding.embedding_space:
                continue
            sim = cosine_similarity(vector, candidate_emb.vector)
            scored.append((trend, sim, payload))

        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[: self._config.recall_top_k]

    async def _adjudicate_gray_zone(
        self,
        *,
        source_meta: dict[str, Any],
        members: list[dict[str, Any]],
        candidate: TrendTheme,
        candidate_payload: dict[str, Any],
        similarity: float,
        embedding_space: str,
        degraded: bool,
        candidate_evidence: dict[str, Any] | None = None,
    ) -> MergeDecision:
        if self._llm is None:
            return MergeDecision(
                action=ClusterDecisionAction.NEEDS_REVIEW,
                target_trend_id=candidate.id,
                similarity=similarity,
                confidence=similarity,
                source=ClusterDecisionSource.LLM,
                reason="llm_unavailable_gray_zone",
                embedding_space=embedding_space,
                degraded=degraded,
                candidate_evidence=candidate_evidence or {},
            )
        prompt = load_prompt_template("cluster_adjudication")
        try:
            result = await self._llm.complete_structured(
                prompt,
                {
                    "source_json": {
                        **source_meta,
                        "member_titles": [m.get("title") for m in members[:5]],
                    },
                    "candidate_json": {
                        "trend_id": str(candidate.id),
                        "canonical_name": candidate.canonical_name,
                        **candidate_payload,
                    },
                    "similarity": round(similarity, 4),
                    "constraint_notes": "hard constraints already passed",
                },
                ClusterAdjudicationResult,
                prompt_name="cluster_adjudication",
            )
        except LlmAdapterError as exc:
            return MergeDecision(
                action=ClusterDecisionAction.NEEDS_REVIEW,
                target_trend_id=candidate.id,
                similarity=similarity,
                confidence=None,
                source=ClusterDecisionSource.LLM,
                reason=f"llm_failed:{exc}",
                embedding_space=embedding_space,
                degraded=degraded,
                candidate_evidence=candidate_evidence or {},
            )

        if result.confidence < self._config.llm_min_confidence:
            action = ClusterDecisionAction.NEEDS_REVIEW
        else:
            action = ClusterDecisionAction(result.action)
        return MergeDecision(
            action=action,
            target_trend_id=(
                candidate.id
                if action
                in {
                    ClusterDecisionAction.MERGE_SAME_ANGLE,
                    ClusterDecisionAction.MERGE_THEME_KEEP_ANGLES_SEPARATE,
                    ClusterDecisionAction.NEEDS_REVIEW,
                }
                else None
            ),
            similarity=similarity,
            confidence=result.confidence,
            source=ClusterDecisionSource.LLM,
            reason=result.reason,
            facet_label=result.facet_label,
            embedding_space=embedding_space,
            degraded=degraded,
            candidate_evidence=candidate_evidence or {},
        )

    async def _trend_is_protected(self, trend_id: uuid.UUID) -> bool:
        brief_hit = await self._session.scalar(
            select(BriefItem.id)
            .join(CreativeAngle, CreativeAngle.id == BriefItem.creative_angle_id)
            .where(CreativeAngle.trend_id == trend_id)
            .limit(1),
        )
        if brief_hit is not None:
            return True
        pub_hit = await self._session.scalar(
            select(PublicationRecord.id)
            .join(CreativeAngle, CreativeAngle.id == PublicationRecord.creative_angle_id)
            .where(
                or_(
                    PublicationRecord.trend_id == trend_id,
                    CreativeAngle.trend_id == trend_id,
                ),
            )
            .limit(1),
        )
        if pub_hit is not None:
            return True
        selected_hit = await self._session.scalar(
            select(DailyCandidate.id)
            .where(
                DailyCandidate.trend_id == trend_id,
                DailyCandidate.selected.is_(True),
            )
            .limit(1),
        )
        return selected_hit is not None
