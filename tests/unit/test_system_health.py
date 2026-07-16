"""Tests for system health helpers."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.system_health import disk_usage, worker_status


def test_disk_usage_structure():
    result = disk_usage("/")
    assert "total_bytes" in result
    assert "used_percent" in result
    assert result["used_percent"] >= 0


@pytest.mark.asyncio
async def test_worker_status_stale_when_no_heartbeat():
    session = MagicMock()
    repo = MagicMock()
    repo.get_heartbeat = AsyncMock(return_value=None)

    with patch("app.services.system_health.OpsRepository", return_value=repo):
        result = await worker_status(session)

    assert result["status"] == "unknown"
    assert result["stale"] is True


@pytest.mark.asyncio
async def test_worker_status_ok_when_recent():
    session = MagicMock()
    heartbeat = MagicMock()
    heartbeat.last_seen_at = datetime.now(UTC) - timedelta(minutes=2)
    heartbeat.details = {"database": "up"}

    repo = MagicMock()
    repo.get_heartbeat = AsyncMock(return_value=heartbeat)

    with patch("app.services.system_health.OpsRepository", return_value=repo):
        result = await worker_status(session)

    assert result["status"] == "ok"
    assert result["stale"] is False
