"""Integration tests for the G4 published-URL workflow (app/services/angle_status.py)."""

from __future__ import annotations

import os
import asyncio
import uuid
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.db import get_session_factory
from app.models import (
    AngleStatus,
    CreativeAngle,
    CreativeFormat,
    DailyCandidate,
    LifecycleStatus,
    Platform,
    PublicationFetchStatus,
    PublicationRecord,
    PublicationStatus,
    TopicType,
    TrendTheme,
)
from app.repositories.creative_angles import CreativeAngleRepository
from app.repositories.daily_candidates import DailyCandidateRepository
from app.services.angle_status import AngleStatusService, PublishedUrlRequired

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS") != "1",
    reason="requires migrated PostgreSQL test database",
)

CANDIDATE_DATE = date(2026, 7, 23)


async def _cleanup(trend_id: uuid.UUID) -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        await session.execute(
            delete(PublicationRecord).where(
                PublicationRecord.creative_angle_id.in_(
                    select(CreativeAngle.id).where(CreativeAngle.trend_id == trend_id),
                ),
            ),
        )
        await session.execute(delete(DailyCandidate).where(DailyCandidate.trend_id == trend_id))
        await session.execute(delete(CreativeAngle).where(CreativeAngle.trend_id == trend_id))
        await session.execute(delete(TrendTheme).where(TrendTheme.id == trend_id))
        await session.commit()


@pytest.mark.asyncio
async def test_publish_without_api_key_persists_retryable_enriched_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No YOUTUBE_API_KEY configured: publish succeeds, record stays PENDING."""
    from app.config import Settings

    monkeypatch.setattr(
        "app.services.publication_metrics.get_settings",
        lambda: Settings(youtube_api_key=""),
    )

    session_factory = get_session_factory()
    trend_id = uuid.uuid4()

    async with session_factory() as session:
        trend = TrendTheme(
            id=trend_id,
            canonical_name="Publication Workflow Trend",
            topic_type=TopicType.ANIME,
            first_detected_at=datetime.now(UTC),
            last_active_at=datetime.now(UTC),
            lifecycle_status=LifecycleStatus.NEW,
        )
        session.add(trend)
        await session.flush()

        angles = CreativeAngleRepository(session)
        angle, _ = await angles.create_angle(
            trend_id=trend_id,
            angle_zh="发布流程测试文案",
            format=CreativeFormat.SHORT,
            evidence_content_ids=[],
            generated_date=CANDIDATE_DATE,
            semantic_fingerprint="publication-workflow-fp",
        )
        angle_id = angle.id

        candidates = DailyCandidateRepository(session)
        daily = await candidates.upsert_candidate(
            candidate_date=CANDIDATE_DATE,
            creative_angle_id=angle_id,
            trend_id=trend_id,
            rank=1,
            candidate_score=1.0,
            score_snapshot=None,
            analysis_run_id=None,
            selected=True,
        )
        daily_candidate_id = daily.id
        await session.commit()

    try:
        async with session_factory() as session:
            angles = CreativeAngleRepository(session)
            angle = await angles.get_by_id(angle_id)
            assert angle is not None
            svc = AngleStatusService(session)
            await svc.transition(angle, AngleStatus.SELECTED)
            await svc.transition(angle, AngleStatus.ADOPTED, daily_candidate_id=daily_candidate_id)

            with pytest.raises(PublishedUrlRequired):
                await svc.transition(
                    angle,
                    AngleStatus.PUBLISHED,
                    published_url="not-a-youtube-link",
                    daily_candidate_id=daily_candidate_id,
                )
            # Failed validation must not partially mutate the in-memory angle.
            assert angle.status == AngleStatus.ADOPTED

            await svc.transition(
                angle,
                AngleStatus.PUBLISHED,
                published_url="https://youtu.be/dQw4w9WgXcQ?t=3",
                daily_candidate_id=daily_candidate_id,
            )
            await session.commit()

        async with session_factory() as session:
            angle = await session.get(CreativeAngle, angle_id)
            assert angle is not None
            assert angle.status == AngleStatus.PUBLISHED

            record = await session.scalar(
                select(PublicationRecord).where(
                    PublicationRecord.creative_angle_id == angle_id,
                    PublicationRecord.status == PublicationStatus.PUBLISHED,
                ),
            )
            assert record is not None
            assert record.external_video_id == "dQw4w9WgXcQ"
            assert record.platform == Platform.YOUTUBE
            assert record.trend_id == trend_id
            assert record.daily_candidate_id == daily_candidate_id
            assert record.published_url == "https://youtu.be/dQw4w9WgXcQ?t=3"
            # No API key: best-effort enrichment is a no-op, record stays retryable.
            assert record.fetch_status == PublicationFetchStatus.PENDING
            assert record.last_fetch_error is None
    finally:
        await _cleanup(trend_id)


@pytest.mark.asyncio
async def test_concurrent_publication_binding_allows_only_one_angle() -> None:
    session_factory = get_session_factory()
    trend_ids = [uuid.uuid4(), uuid.uuid4()]
    angle_ids = [uuid.uuid4(), uuid.uuid4()]
    video_id = uuid.uuid4().hex[:11]

    async with session_factory() as session:
        for index, (trend_id, angle_id) in enumerate(zip(trend_ids, angle_ids)):
            session.add(
                TrendTheme(
                    id=trend_id,
                    canonical_name=f"Concurrent Publication {index}",
                    topic_type=TopicType.ANIME,
                    first_detected_at=datetime.now(UTC),
                    last_active_at=datetime.now(UTC),
                    lifecycle_status=LifecycleStatus.NEW,
                ),
            )
            session.add(
                CreativeAngle(
                    id=angle_id,
                    trend_id=trend_id,
                    angle_zh=f"并发发布 {index}",
                    format=CreativeFormat.SHORT,
                    evidence_content_ids=[],
                    generated_date=CANDIDATE_DATE,
                    semantic_fingerprint=f"concurrent-publication-{index}-{video_id}",
                ),
            )
        await session.commit()

    async def bind(angle_id: uuid.UUID) -> bool:
        async with session_factory() as session:
            session.add(
                PublicationRecord(
                    creative_angle_id=angle_id,
                    status=PublicationStatus.PUBLISHED,
                    platform=Platform.YOUTUBE,
                    external_video_id=video_id,
                    published_url=f"https://youtu.be/{video_id}",
                    published_at=datetime.now(UTC),
                ),
            )
            try:
                await session.commit()
                return True
            except IntegrityError:
                await session.rollback()
                return False

    try:
        results = await asyncio.gather(*(bind(angle_id) for angle_id in angle_ids))
        assert sum(results) == 1
    finally:
        for trend_id in trend_ids:
            await _cleanup(trend_id)
