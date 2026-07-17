from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import delete, select

from app.db import get_session_factory
from app.models import (
    ClusterDecisionAudit,
    ContentItem,
    LifecycleStatus,
    MembershipMethod,
    Platform,
    TopicType,
    TrendMember,
    TrendTheme,
)
from app.repositories.trends import TrendsRepository
from app.services.trend_consistency import TrendConsistencyService

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS") != "1",
    reason="requires migrated PostgreSQL test database",
)


async def _cleanup(trend_ids: list[uuid.UUID], content_ids: list[uuid.UUID]) -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        await session.execute(
            delete(ClusterDecisionAudit).where(
                ClusterDecisionAudit.target_trend_id.in_(trend_ids),
            ),
        )
        await session.execute(delete(TrendMember).where(TrendMember.trend_id.in_(trend_ids)))
        await session.execute(delete(ContentItem).where(ContentItem.id.in_(content_ids)))
        await session.execute(delete(TrendTheme).where(TrendTheme.id.in_(trend_ids)))
        await session.commit()


async def _seed() -> tuple[list[uuid.UUID], list[uuid.UUID]]:
    trend_ids = [uuid.uuid4(), uuid.uuid4()]
    content_ids = [uuid.uuid4(), uuid.uuid4()]
    session_factory = get_session_factory()
    async with session_factory() as session:
        for index, trend_id in enumerate(trend_ids):
            session.add(
                TrendTheme(
                    id=trend_id,
                    canonical_name=f"Consistency Trend {index}",
                    topic_type=TopicType.ANIME,
                    first_detected_at=datetime.now(UTC),
                    last_active_at=datetime.now(UTC),
                    lifecycle_status=LifecycleStatus.RISING,
                ),
            )
        for index, content_id in enumerate(content_ids):
            session.add(
                ContentItem(
                    id=content_id,
                    platform=Platform.YOUTUBE,
                    external_id=f"consistency-{content_id}",
                    title_original=f"Content {index}",
                ),
            )
        session.add(
            TrendMember(
                trend_id=trend_ids[0],
                content_item_id=content_ids[0],
                membership_method=MembershipMethod.RULE,
                membership_score=0.91,
                active=True,
                last_confirmed_at=datetime.now(UTC),
            ),
        )
        await session.commit()
    return trend_ids, content_ids


@pytest.mark.asyncio
async def test_manual_move_out_is_sticky_until_explicit_manual_restore() -> None:
    trend_ids, content_ids = await _seed()
    session_factory = get_session_factory()
    try:
        async with session_factory() as session:
            service = TrendConsistencyService(session)
            await service.manual_move_out(
                trend_id=trend_ids[0],
                content_item_id=content_ids[0],
            )
            await session.commit()
            await service.close()

        async with session_factory() as session:
            await TrendsRepository(session).sync_members(
                trend_ids[0],
                [
                    {
                        "content_item_id": content_ids[0],
                        "membership_method": MembershipMethod.LLM,
                    },
                ],
                membership_method=MembershipMethod.LLM,
            )
            await session.commit()

        async with session_factory() as session:
            member = await session.scalar(
                select(TrendMember).where(
                    TrendMember.trend_id == trend_ids[0],
                    TrendMember.content_item_id == content_ids[0],
                ),
            )
            assert member is not None
            assert member.active is False
            assert member.membership_method == MembershipMethod.MANUAL

            service = TrendConsistencyService(session)
            await service.manual_restore_member(
                trend_id=trend_ids[0],
                content_item_id=content_ids[0],
            )
            await session.commit()
            await service.close()
            assert member.active is True
            assert member.membership_method == MembershipMethod.MANUAL
    finally:
        await _cleanup(trend_ids, content_ids)


@pytest.mark.asyncio
async def test_manual_merge_rollback_restores_snapshot_only_and_is_idempotent() -> None:
    trend_ids, content_ids = await _seed()
    session_factory = get_session_factory()
    try:
        async with session_factory() as session:
            service = TrendConsistencyService(session)
            audit = await service.manual_merge(
                source_trend_id=trend_ids[0],
                target_trend_id=trend_ids[1],
            )
            audit_id = audit.id
            await session.commit()
            await service.close()

        async with session_factory() as session:
            session.add(
                TrendMember(
                    trend_id=trend_ids[1],
                    content_item_id=content_ids[1],
                    membership_method=MembershipMethod.RULE,
                    active=True,
                    last_confirmed_at=datetime.now(UTC),
                ),
            )
            await session.commit()

        async with session_factory() as session:
            service = TrendConsistencyService(session)
            first_rollback = await service.rollback_decision(audit_id)
            first_rollback_id = first_rollback.id
            await session.commit()
            second_rollback = await service.rollback_decision(audit_id)
            await session.commit()
            await service.close()
            assert second_rollback.id == first_rollback_id

        async with session_factory() as session:
            original = await session.scalar(
                select(TrendMember).where(
                    TrendMember.content_item_id == content_ids[0],
                    TrendMember.active.is_(True),
                ),
            )
            later = await session.scalar(
                select(TrendMember).where(
                    TrendMember.content_item_id == content_ids[1],
                    TrendMember.active.is_(True),
                ),
            )
            source = await session.get(TrendTheme, trend_ids[0])
            assert original is not None and original.trend_id == trend_ids[0]
            assert later is not None and later.trend_id == trend_ids[1]
            assert source is not None and source.active is True
            assert source.lifecycle_status == LifecycleStatus.RISING
    finally:
        await _cleanup(trend_ids, content_ids)
