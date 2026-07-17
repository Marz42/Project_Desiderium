from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.membership_policy import (
    may_reactivate_membership,
    membership_method_priority,
)
from app.models import (
    LifecycleStatus,
    MembershipMethod,
    TopicType,
    TrendMember,
    TrendScoreSnapshot,
    TrendTheme,
)


class TrendsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, trend_id: uuid.UUID) -> TrendTheme | None:
        return await self._session.get(TrendTheme, trend_id)

    async def list_score_snapshots(
        self, trend_id: uuid.UUID, *, limit: int = 30
    ) -> list[TrendScoreSnapshot]:
        stmt = (
            select(TrendScoreSnapshot)
            .where(TrendScoreSnapshot.trend_id == trend_id)
            .order_by(TrendScoreSnapshot.snapshot_date.desc())
            .limit(limit)
        )
        return list((await self._session.scalars(stmt)).all())

    async def list_members_with_content(
        self,
        trend_id: uuid.UUID,
        *,
        active_only: bool = True,
    ) -> list[TrendMember]:
        from sqlalchemy.orm import selectinload

        stmt = (
            select(TrendMember)
            .where(TrendMember.trend_id == trend_id)
            .options(selectinload(TrendMember.content_item))
            .order_by(TrendMember.added_at.desc())
        )
        if active_only:
            stmt = stmt.where(TrendMember.active.is_(True))
        return list((await self._session.scalars(stmt)).all())

    async def get_by_canonical_name(self, canonical_name: str) -> TrendTheme | None:
        stmt = select(TrendTheme).where(
            TrendTheme.canonical_name == canonical_name,
            TrendTheme.active.is_(True),
        )
        return await self._session.scalar(stmt)

    async def get_by_entity_id(self, entity_id: str) -> TrendTheme | None:
        stmt = select(TrendTheme).where(
            TrendTheme.entities["entity_id"].astext == entity_id,
            TrendTheme.active.is_(True),
        )
        return await self._session.scalar(stmt)

    async def list_active_trends(self) -> list[TrendTheme]:
        stmt = select(TrendTheme).where(
            TrendTheme.active.is_(True),
            TrendTheme.lifecycle_status != LifecycleStatus.DORMANT,
        )
        result = await self._session.scalars(stmt)
        return list(result.all())

    async def upsert_trend(
        self,
        *,
        entity_id: str,
        canonical_name: str,
        anime_title: str | None,
        topic_type: TopicType,
        entities: dict,
        score: float,
        score_components: dict,
        confidence: float,
        lifecycle_status: LifecycleStatus,
        now: datetime,
        existing: TrendTheme | None = None,
    ) -> TrendTheme:
        if existing is None:
            existing = await self.get_by_entity_id(entity_id)
        if existing is None:
            existing = await self.get_by_canonical_name(canonical_name)

        if existing is not None:
            existing.canonical_name = canonical_name
            existing.anime_title = anime_title or None
            existing.topic_type = topic_type
            existing.entities = entities
            existing.score = score
            existing.score_components = score_components
            existing.confidence = confidence
            existing.lifecycle_status = lifecycle_status
            existing.last_active_at = now
            existing.updated_at = now
            await self._session.flush()
            return existing

        trend = TrendTheme(
            canonical_name=canonical_name,
            anime_title=anime_title or None,
            topic_type=topic_type,
            entities=entities,
            first_detected_at=now,
            last_active_at=now,
            lifecycle_status=lifecycle_status,
            score=score,
            score_components=score_components,
            confidence=confidence,
        )
        self._session.add(trend)
        await self._session.flush()
        return trend

    async def sync_members(
        self,
        trend_id: uuid.UUID,
        members: list[dict[str, Any]],
        *,
        now: datetime | None = None,
        membership_method: MembershipMethod = MembershipMethod.RULE,
    ) -> dict[str, int]:
        """Upsert active members and soft-deactivate missing ones."""
        now = now or datetime.now(UTC)
        stmt = select(TrendMember).where(TrendMember.trend_id == trend_id)
        existing = list((await self._session.scalars(stmt)).all())
        by_content = {row.content_item_id: row for row in existing}
        seen: set[uuid.UUID] = set()
        created = 0
        reactivated = 0
        confirmed = 0

        for member in members:
            content_id = member["content_item_id"]
            if isinstance(content_id, str):
                content_id = uuid.UUID(content_id)
            seen.add(content_id)
            method = member.get("membership_method", membership_method)
            if isinstance(method, str):
                method = MembershipMethod(method)
            row = by_content.get(content_id)
            if row is None:
                self._session.add(
                    TrendMember(
                        trend_id=trend_id,
                        content_item_id=content_id,
                        membership_score=member.get("membership_score"),
                        membership_method=method,
                        evidence=member.get("evidence"),
                        active=True,
                        added_at=now,
                        last_confirmed_at=now,
                        deactivated_at=None,
                    ),
                )
                created += 1
                continue
            was_inactive = not row.active
            if not may_reactivate_membership(row.membership_method, row.active, method):
                continue
            method_changed = False
            if membership_method_priority(method) >= membership_method_priority(
                row.membership_method
            ):
                method_changed = method != row.membership_method
                row.membership_score = member.get("membership_score")
                row.membership_method = method
                row.evidence = member.get("evidence")
            row.active = True
            row.last_confirmed_at = now
            row.deactivated_at = None
            if was_inactive or method_changed:
                row.decision_version += 1
            if was_inactive:
                reactivated += 1
            else:
                confirmed += 1

        deactivated = 0
        for content_id, row in by_content.items():
            if content_id in seen or not row.active:
                continue
            if (
                row.membership_method == MembershipMethod.MANUAL
                and membership_method != MembershipMethod.MANUAL
            ):
                continue
            row.active = False
            row.deactivated_at = now
            row.decision_version += 1
            deactivated += 1

        await self._session.flush()
        return {
            "created": created,
            "reactivated": reactivated,
            "confirmed": confirmed,
            "deactivated": deactivated,
        }

    async def replace_members(
        self,
        trend_id: uuid.UUID,
        members: list[dict],
    ) -> None:
        """Backward-compatible wrapper around soft-sync membership."""
        await self.sync_members(trend_id, members)

    async def upsert_score_snapshot(
        self,
        *,
        trend_id: uuid.UUID,
        snapshot_date: date,
        score: float,
        score_components: dict,
        lifecycle_status: LifecycleStatus,
        member_count: int,
        channel_count: int,
    ) -> TrendScoreSnapshot:
        values = {
            "trend_id": trend_id,
            "snapshot_date": snapshot_date,
            "score": score,
            "score_components": score_components,
            "lifecycle_status": lifecycle_status,
            "member_count": member_count,
            "channel_count": channel_count,
        }
        stmt = (
            insert(TrendScoreSnapshot)
            .values(id=uuid.uuid4(), **values)
            .on_conflict_do_update(
                index_elements=["trend_id", "snapshot_date"],
                set_={
                    "score": values["score"],
                    "score_components": values["score_components"],
                    "lifecycle_status": values["lifecycle_status"],
                    "member_count": values["member_count"],
                    "channel_count": values["channel_count"],
                },
            )
            .returning(TrendScoreSnapshot.id)
        )
        result = await self._session.execute(stmt)
        row_id = result.scalar_one()
        row = await self._session.get(TrendScoreSnapshot, row_id)
        assert row is not None
        return row

    async def get_score_snapshot(
        self,
        trend_id: uuid.UUID,
        snapshot_date: date,
    ) -> TrendScoreSnapshot | None:
        stmt = select(TrendScoreSnapshot).where(
            TrendScoreSnapshot.trend_id == trend_id,
            TrendScoreSnapshot.snapshot_date == snapshot_date,
        )
        return await self._session.scalar(stmt)

    async def get_previous_score_snapshot(
        self,
        trend_id: uuid.UUID,
        before_date: date,
    ) -> TrendScoreSnapshot | None:
        stmt = (
            select(TrendScoreSnapshot)
            .where(
                TrendScoreSnapshot.trend_id == trend_id,
                TrendScoreSnapshot.snapshot_date < before_date,
            )
            .order_by(TrendScoreSnapshot.snapshot_date.desc())
            .limit(1)
        )
        return await self._session.scalar(stmt)
