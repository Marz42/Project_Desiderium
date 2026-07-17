"""Integration tests for brief GET read-only + explicit sync/finalize (G4-B)."""

from __future__ import annotations

import os
import asyncio
import uuid
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import delete, select

from app.db import get_session_factory
from app.models import (
    Brief,
    BriefItem,
    BriefStatus,
    CreativeAngle,
    CreativeFormat,
    DailyCandidate,
    LifecycleStatus,
    TopicType,
    TrendTheme,
)
from app.repositories.briefs import BriefRepository
from app.repositories.daily_candidates import DailyCandidateRepository
from app.services.brief_export import BriefExportService

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS") != "1",
    reason="requires migrated PostgreSQL test database",
)

BRIEF_DATE = date(2026, 7, 22)


async def _cleanup(trend_id: uuid.UUID) -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        await session.execute(delete(DailyCandidate).where(DailyCandidate.trend_id == trend_id))
        await session.execute(delete(CreativeAngle).where(CreativeAngle.trend_id == trend_id))
        await session.execute(delete(TrendTheme).where(TrendTheme.id == trend_id))
        brief = await session.scalar(select(Brief).where(Brief.brief_date == BRIEF_DATE))
        if brief is not None:
            await session.execute(delete(BriefItem).where(BriefItem.brief_id == brief.id))
            await session.delete(brief)
        await session.commit()


@pytest.mark.asyncio
async def test_get_preview_never_syncs_or_persists_a_brief_row() -> None:
    session_factory = get_session_factory()
    trend_id = uuid.uuid4()

    async with session_factory() as session:
        trend = TrendTheme(
            id=trend_id,
            canonical_name="Brief Workflow Trend",
            topic_type=TopicType.ANIME,
            first_detected_at=datetime.now(UTC),
            last_active_at=datetime.now(UTC),
            lifecycle_status=LifecycleStatus.NEW,
        )
        session.add(trend)
        await session.flush()

        angle = CreativeAngle(
            id=uuid.uuid4(),
            trend_id=trend_id,
            angle_zh="原始文案",
            format=CreativeFormat.SHORT,
            evidence_content_ids=[],
            generated_date=BRIEF_DATE,
            semantic_fingerprint="brief-workflow-fp",
        )
        session.add(angle)
        await session.flush()
        angle_id = angle.id

        candidates = DailyCandidateRepository(session)
        await candidates.upsert_candidate(
            candidate_date=BRIEF_DATE,
            creative_angle_id=angle_id,
            trend_id=trend_id,
            rank=1,
            candidate_score=1.0,
            score_snapshot=None,
            analysis_run_id=None,
            selected=True,
        )
        await session.commit()

    try:
        # GET-only read: must not create/persist a Brief row nor sync items.
        async with session_factory() as session:
            service = BriefExportService(session)
            data = await service.get_preview_data(BRIEF_DATE)
            assert data["sections"] == []
            # Deliberately no commit() here, mirroring the read-only GET route.

        async with session_factory() as session:
            leaked = await session.scalar(select(Brief).where(Brief.brief_date == BRIEF_DATE))
            assert leaked is None, "GET preview must not persist a Brief row"

        # Explicit sync (POST) actually populates the draft.
        async with session_factory() as session:
            service = BriefExportService(session)
            await service.sync_brief_from_selection(BRIEF_DATE)

        async with session_factory() as session:
            service = BriefExportService(session)
            data = await service.get_preview_data(BRIEF_DATE)
            assert len(data["sections"]) == 1
            assert len(data["sections"][0]["angles"]) == 1
            assert data["brief"].status == BriefStatus.DRAFT
            assert data["brief"].exported_at is None
    finally:
        await _cleanup(trend_id)


@pytest.mark.asyncio
async def test_finalize_freezes_snapshot_independent_of_later_edits() -> None:
    session_factory = get_session_factory()
    trend_id = uuid.uuid4()
    angle_id = uuid.uuid4()

    async with session_factory() as session:
        trend = TrendTheme(
            id=trend_id,
            canonical_name="Finalize Trend",
            topic_type=TopicType.ANIME,
            first_detected_at=datetime.now(UTC),
            last_active_at=datetime.now(UTC),
            lifecycle_status=LifecycleStatus.NEW,
        )
        session.add(trend)
        angle = CreativeAngle(
            id=angle_id,
            trend_id=trend_id,
            angle_zh="固化前文案",
            format=CreativeFormat.SHORT,
            evidence_content_ids=[],
            generated_date=BRIEF_DATE,
            semantic_fingerprint="finalize-fp",
        )
        session.add(angle)
        await session.flush()

        candidates = DailyCandidateRepository(session)
        await candidates.upsert_candidate(
            candidate_date=BRIEF_DATE,
            creative_angle_id=angle_id,
            trend_id=trend_id,
            rank=1,
            candidate_score=1.0,
            score_snapshot=None,
            analysis_run_id=None,
            selected=True,
        )
        await session.commit()

    try:
        async with session_factory() as session:
            service = BriefExportService(session)
            await service.sync_brief_from_selection(BRIEF_DATE)

        async with session_factory() as session:
            service = BriefExportService(session)
            finalized = await service.finalize_brief(BRIEF_DATE)
            assert finalized is not None
            assert finalized.status == BriefStatus.FINALIZED
            assert finalized.finalized_content_hash is not None
            assert finalized.finalized_snapshot is not None

        # Mutate the underlying angle after finalizing.
        async with session_factory() as session:
            angle = await session.get(CreativeAngle, angle_id)
            assert angle is not None
            angle.angle_zh = "固化后修改的文案"
            await session.commit()

        async with session_factory() as session:
            service = BriefExportService(session)
            markdown = await service.render_markdown(BRIEF_DATE)
            assert "固化前文案" in markdown
            assert "固化后修改的文案" not in markdown

            # The live draft preview still reflects the current (mutated) data;
            # only export rendering prefers the frozen snapshot.
            data = await service.get_preview_data(BRIEF_DATE)
            assert data["sections"][0]["angles"][0]["angle"].angle_zh == "固化后修改的文案"

        # mark_exported must not demote an already-finalized brief.
        async with session_factory() as session:
            service = BriefExportService(session)
            await service.mark_exported(BRIEF_DATE)

        async with session_factory() as session:
            repo = BriefRepository(session)
            brief = await repo.get_by_date(BRIEF_DATE)
            assert brief is not None
            assert brief.status == BriefStatus.FINALIZED
            assert brief.exported_at is not None
    finally:
        await _cleanup(trend_id)


@pytest.mark.asyncio
async def test_concurrent_finalize_keeps_one_immutable_snapshot() -> None:
    session_factory = get_session_factory()
    concurrent_date = date(2026, 7, 24)
    async with session_factory() as session:
        brief = Brief(
            brief_date=concurrent_date,
            title="Concurrent Finalize",
            status=BriefStatus.DRAFT,
            items=[],
        )
        session.add(brief)
        await session.commit()
        brief_id = brief.id

    async def finalize(snapshot_value: str, actor: str) -> None:
        async with session_factory() as session:
            await BriefRepository(session).finalize(
                brief_id,
                [{"value": snapshot_value}],
                snapshot_value * 64,
                finalized_by=actor,
            )
            await session.commit()

    try:
        await asyncio.gather(
            finalize("a", "admin-a"),
            finalize("b", "admin-b"),
        )
        async with session_factory() as session:
            brief = await session.get(Brief, brief_id)
            assert brief is not None
            assert brief.finalized_snapshot in ([{"value": "a"}], [{"value": "b"}])
            expected_value = brief.finalized_snapshot[0]["value"]
            assert brief.finalized_content_hash == expected_value * 64
            assert brief.finalized_by == f"admin-{expected_value}"
            first_finalized_at = brief.finalized_at

        async with session_factory() as session:
            await BriefRepository(session).finalize(
                brief_id,
                [{"value": "c"}],
                "c" * 64,
                finalized_by="admin-c",
            )
            await session.commit()
        async with session_factory() as session:
            brief = await session.get(Brief, brief_id)
            assert brief is not None
            assert brief.finalized_at == first_finalized_at
            assert brief.finalized_content_hash == expected_value * 64
    finally:
        async with session_factory() as session:
            brief = await session.get(Brief, brief_id)
            if brief is not None:
                await session.delete(brief)
            await session.commit()
