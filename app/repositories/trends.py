from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

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

    async def get_by_canonical_name(self, canonical_name: str) -> TrendTheme | None:
        stmt = select(TrendTheme).where(TrendTheme.canonical_name == canonical_name)
        return await self._session.scalar(stmt)

    async def get_by_entity_id(self, entity_id: str) -> TrendTheme | None:
        stmt = select(TrendTheme).where(
            TrendTheme.entities["entity_id"].astext == entity_id,
        )
        return await self._session.scalar(stmt)

    async def list_active_trends(self) -> list[TrendTheme]:
        stmt = select(TrendTheme).where(
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

    async def replace_members(
        self,
        trend_id: uuid.UUID,
        members: list[dict],
    ) -> None:
        await self._session.execute(
            delete(TrendMember).where(TrendMember.trend_id == trend_id),
        )
        for member in members:
            self._session.add(
                TrendMember(
                    trend_id=trend_id,
                    content_item_id=member["content_item_id"],
                    membership_score=member.get("membership_score"),
                    membership_method=MembershipMethod.RULE,
                    evidence=member.get("evidence"),
                ),
            )

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
