"""Unit tests for creative angle status machine."""

from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import (
    AngleStatus,
    AngleStatusAudit,
    CreativeAngle,
    CreativeFormat,
    Platform,
    PublicationFetchStatus,
    PublicationRecord,
    PublicationStatus,
)
from app.services.angle_status import (
    VALID_TRANSITIONS,
    AngleStatusService,
    PublishedUrlChangeConflict,
    PublishedUrlConflict,
    PublishedUrlRequired,
)


def _make_angle(status: AngleStatus = AngleStatus.ADOPTED) -> CreativeAngle:
    return CreativeAngle(
        id=uuid.uuid4(),
        trend_id=uuid.uuid4(),
        status=status,
        angle_zh="测试方向",
        format=CreativeFormat.SHORT,
        generated_date=date.today(),
    )


def test_valid_transitions_from_candidate() -> None:
    allowed = VALID_TRANSITIONS[AngleStatus.CANDIDATE]
    assert AngleStatus.SELECTED in allowed
    assert AngleStatus.BLOCKED in allowed
    assert AngleStatus.ADOPTED not in allowed


def test_valid_transitions_from_selected() -> None:
    allowed = VALID_TRANSITIONS[AngleStatus.SELECTED]
    assert AngleStatus.ADOPTED in allowed
    assert AngleStatus.CANDIDATE in allowed
    assert AngleStatus.BLOCKED in allowed


def test_can_transition_same_status() -> None:
    svc = AngleStatusService(session=None)  # type: ignore[arg-type]
    assert svc.can_transition(AngleStatus.CANDIDATE, AngleStatus.CANDIDATE)


def test_invalid_transition_raises() -> None:
    svc = AngleStatusService(session=None)  # type: ignore[arg-type]
    assert not svc.can_transition(AngleStatus.CANDIDATE, AngleStatus.PUBLISHED)


def test_blocked_is_terminal() -> None:
    assert VALID_TRANSITIONS[AngleStatus.BLOCKED] == set()


@pytest.mark.asyncio
async def test_publish_without_url_raises_published_url_required() -> None:
    svc = AngleStatusService(session=None)  # type: ignore[arg-type]
    angle = _make_angle()
    with pytest.raises(PublishedUrlRequired):
        await svc.transition(angle, AngleStatus.PUBLISHED, published_url=None)
    assert angle.status == AngleStatus.ADOPTED


@pytest.mark.asyncio
async def test_publish_with_non_youtube_url_raises_published_url_required() -> None:
    svc = AngleStatusService(session=None)  # type: ignore[arg-type]
    angle = _make_angle()
    with pytest.raises(PublishedUrlRequired):
        await svc.transition(
            angle, AngleStatus.PUBLISHED, published_url="https://vimeo.com/12345678"
        )
    assert angle.status == AngleStatus.ADOPTED


@pytest.mark.asyncio
async def test_publish_with_valid_youtube_url_creates_retryable_publication_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # No API key configured: enrichment must be a no-op, never raise, and
    # leave the record retryable (PENDING) rather than rolling back status.
    monkeypatch.setattr(
        "app.services.publication_metrics.PublicationMetricsService._build_adapter",
        lambda self: None,
    )
    session = AsyncMock(spec=AsyncSession)
    session.scalar.side_effect = [None, None]
    svc = AngleStatusService(session=session)
    angle = _make_angle()

    updated = await svc.transition(
        angle,
        AngleStatus.PUBLISHED,
        published_url="https://youtu.be/dQw4w9WgXcQ",
    )

    assert updated.status == AngleStatus.PUBLISHED
    added = [call.args[0] for call in session.add.call_args_list]
    audit = next(obj for obj in added if isinstance(obj, AngleStatusAudit))
    record = next(obj for obj in added if isinstance(obj, PublicationRecord))
    assert audit.to_status == AngleStatus.PUBLISHED
    assert record.external_video_id == "dQw4w9WgXcQ"
    assert record.platform == Platform.YOUTUBE
    assert record.fetch_status == PublicationFetchStatus.PENDING
    assert record.published_url == "https://youtu.be/dQw4w9WgXcQ"
    assert record.trend_id == angle.trend_id


@pytest.mark.asyncio
async def test_publish_api_failure_does_not_roll_back_angle_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """API failure during enrichment must not raise nor revert the transition."""

    class _RaisingAdapter:
        async def fetch_item_details(self, ids: list[str]) -> list[dict]:
            raise RuntimeError("youtube api unavailable")

        async def close(self) -> None:
            return None

    monkeypatch.setattr(
        "app.services.publication_metrics.get_settings",
        lambda: Settings(youtube_api_key="fake-key-for-test"),
    )
    monkeypatch.setattr(
        "app.services.publication_metrics.PublicationMetricsService._build_adapter",
        lambda self: _RaisingAdapter(),
    )
    session = AsyncMock(spec=AsyncSession)
    session.scalar.side_effect = [None, None]
    svc = AngleStatusService(session=session)
    angle = _make_angle()

    updated = await svc.transition(
        angle,
        AngleStatus.PUBLISHED,
        published_url="https://youtu.be/dQw4w9WgXcQ",
    )

    assert updated.status == AngleStatus.PUBLISHED
    added = [call.args[0] for call in session.add.call_args_list]
    record = next(obj for obj in added if isinstance(obj, PublicationRecord))
    assert record.fetch_status == PublicationFetchStatus.FAILED
    assert record.last_fetch_error is not None


@pytest.mark.asyncio
async def test_publish_rejects_video_bound_to_another_angle() -> None:
    angle = _make_angle()
    existing = PublicationRecord(
        creative_angle_id=uuid.uuid4(),
        status=PublicationStatus.PUBLISHED,
        platform=Platform.YOUTUBE,
        external_video_id="dQw4w9WgXcQ",
    )
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = existing

    with pytest.raises(PublishedUrlConflict):
        await AngleStatusService(session).transition(
            angle,
            AngleStatus.PUBLISHED,
            published_url="https://youtube.com/watch?v=dQw4w9WgXcQ&utm_source=test",
        )
    assert angle.status == AngleStatus.ADOPTED


@pytest.mark.asyncio
async def test_publish_same_angle_and_video_is_idempotent() -> None:
    angle = _make_angle()
    existing = PublicationRecord(
        creative_angle_id=angle.id,
        status=PublicationStatus.PUBLISHED,
        platform=Platform.YOUTUBE,
        external_video_id="dQw4w9WgXcQ",
    )
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = existing

    updated = await AngleStatusService(session).transition(
        angle,
        AngleStatus.PUBLISHED,
        published_url="https://youtu.be/dQw4w9WgXcQ",
    )

    assert updated.status == AngleStatus.PUBLISHED
    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_published_resubmit_same_video_is_idempotent() -> None:
    angle = _make_angle(status=AngleStatus.PUBLISHED)
    existing = PublicationRecord(
        creative_angle_id=angle.id,
        status=PublicationStatus.PUBLISHED,
        platform=Platform.YOUTUBE,
        external_video_id="dQw4w9WgXcQ",
    )
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = existing

    updated = await AngleStatusService(session).transition(
        angle,
        AngleStatus.PUBLISHED,
        published_url="https://youtu.be/dQw4w9WgXcQ",
    )

    assert updated.status == AngleStatus.PUBLISHED
    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_published_resubmit_different_video_raises_change_conflict() -> None:
    angle = _make_angle(status=AngleStatus.PUBLISHED)
    existing = PublicationRecord(
        creative_angle_id=angle.id,
        status=PublicationStatus.PUBLISHED,
        platform=Platform.YOUTUBE,
        external_video_id="dQw4w9WgXcQ",
    )
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = existing

    with pytest.raises(PublishedUrlChangeConflict):
        await AngleStatusService(session).transition(
            angle,
            AngleStatus.PUBLISHED,
            published_url="https://youtu.be/abc123XYZ00",
        )
