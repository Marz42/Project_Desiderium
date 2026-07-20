"""Tests for /admin/status ops dashboard."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import get_settings
from app.web.session import SESSION_COOKIE, sign_session


@pytest.mark.asyncio
async def test_admin_status_returns_dashboard(client):
    payload = {
        "generated_at": "2026-07-17T00:00:00+00:00",
        "environment": "test",
        "health": {"status": "ok"},
        "task_failures_24h": {"failed_total": 0, "running": 0, "recent_failures": []},
        "youtube_quota_usage": {
            "quota_used": 100,
            "quota_limit": 10000,
            "exhausted": False,
        },
        "llm_usage_today": {"total_tokens": 0, "cost_usd_estimate": 0.0},
        "metric_snapshots": {"total": 10, "retention_days": 90},
        "disk": {"used_percent": 40.0},
    }

    mock_service = MagicMock()
    mock_service.get_status = AsyncMock(return_value=payload)

    settings = get_settings()
    client.cookies.set(
        SESSION_COOKIE,
        sign_session({"authenticated": True}, settings.secret_key),
    )

    with patch("app.web.routes.admin_status.OpsStatusService", return_value=mock_service):
        response = await client.get("/admin/status")

    assert response.status_code == 200
    body = response.json()
    assert body["youtube_quota_usage"]["quota_used"] == 100
    assert body["metric_snapshots"]["retention_days"] == 90
