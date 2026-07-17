from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    PublicationRecord,
    PublicationStatus,
    PublicationWindowKey,
)
from app.services.publication_metrics import PublicationMetricsService


def _record(*, age_hours: float) -> PublicationRecord:
    now = datetime(2026, 7, 17, 12, tzinfo=UTC)
    return PublicationRecord(
        id=uuid.uuid4(),
        creative_angle_id=uuid.uuid4(),
        status=PublicationStatus.PUBLISHED,
        external_video_id="dQw4w9WgXcQ",
        published_at=now - timedelta(hours=age_hours),
        metric_snapshots=[],
    )


@pytest.mark.asyncio
async def test_late_record_captures_only_latest_mature_window() -> None:
    now = datetime(2026, 7, 17, 12, tzinfo=UTC)
    service = PublicationMetricsService(AsyncMock(spec=AsyncSession))

    due = await service._due_windows(_record(age_hours=100), now)

    assert due == [(PublicationWindowKey.H72, 72)]


@pytest.mark.asyncio
async def test_unmatured_windows_are_not_due_or_failures() -> None:
    now = datetime(2026, 7, 17, 12, tzinfo=UTC)
    service = PublicationMetricsService(AsyncMock(spec=AsyncSession))

    due = await service._due_windows(_record(age_hours=25), now)

    assert due == [(PublicationWindowKey.H24, 24)]
    assert PublicationWindowKey.H72 not in {key for key, _ in due}
    assert PublicationWindowKey.D7 not in {key for key, _ in due}


def test_repeated_fetch_failures_enter_terminal_backoff() -> None:
    service = PublicationMetricsService(AsyncMock(spec=AsyncSession))
    record = _record(age_hours=200)
    now = datetime(2026, 7, 17, 12, tzinfo=UTC)

    for _ in range(service._config.publication.max_consecutive_failures):
        service._record_failure(record, RuntimeError("private"), now=now)

    assert record.terminal_fetch_failure is True
    assert record.next_retry_at is not None
    assert record.next_retry_at > now
