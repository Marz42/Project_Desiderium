"""PostgreSQL integration checks for Beta hardening invariants."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import delete, func, select

from app.db import get_session_factory
from app.models import CreativeAngle, CreativeFormat, LifecycleStatus, TopicType, TrendTheme
from app.repositories.analysis_runs import AnalysisRunRepository
from app.repositories.creative_angles import CreativeAngleRepository

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS") != "1",
    reason="requires migrated PostgreSQL test database",
)


@pytest.mark.asyncio
async def test_angle_and_analysis_run_writes_are_idempotent() -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        trend = TrendTheme(
            id=uuid.uuid4(),
            canonical_name="Integration Trend",
            topic_type=TopicType.ANIME,
            first_detected_at=datetime.now(UTC),
            last_active_at=datetime.now(UTC),
            lifecycle_status=LifecycleStatus.NEW,
        )
        session.add(trend)
        await session.flush()

        angles = CreativeAngleRepository(session)
        kwargs = {
            "trend_id": trend.id,
            "angle_zh": "相同方向",
            "format": CreativeFormat.SHORT,
            "evidence_content_ids": ["video-1"],
            "generated_date": date(2026, 7, 17),
            "semantic_fingerprint": "same-fingerprint",
        }
        first, first_created = await angles.create_angle(**kwargs)
        second, second_created = await angles.create_angle(**kwargs)
        assert first.id == second.id
        assert first_created is True
        assert second_created is False
        count = await session.scalar(
            select(func.count())
            .select_from(CreativeAngle)
            .where(CreativeAngle.trend_id == trend.id),
        )
        assert count == 1

        runs = AnalysisRunRepository(session)
        run_kwargs = {
            "run_date": date(2026, 7, 17),
            "run_kind": f"integration-{trend.id}",
            "scoring_version": "test",
            "algorithm_version": "test",
            "config_hash": "0" * 64,
            "run_fingerprint": "1" * 64,
            "config_snapshot": {"test": True},
            "prompt_versions": {"test": "1"},
        }
        retry_id = uuid.uuid4()
        first_run = await runs.start(**run_kwargs, analysis_run_id=retry_id)
        second_run = await runs.start(**run_kwargs, analysis_run_id=retry_id)
        assert first_run.id == second_run.id
        independent_run = await runs.start(**run_kwargs)
        assert independent_run.id != first_run.id

        await session.execute(delete(CreativeAngle).where(CreativeAngle.trend_id == trend.id))
        await session.delete(first_run)
        await session.delete(independent_run)
        await session.delete(trend)
        await session.commit()
