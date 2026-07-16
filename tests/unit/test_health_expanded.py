"""Tests for expanded /health endpoint."""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_health_comprehensive_ok(client):
    payload = {
        "status": "ok",
        "database": "up",
        "disk": {"used_percent": 50.0, "status": "ok"},
        "worker": {"status": "ok", "stale": False},
        "environment": "development",
    }
    with patch("app.web.routes.health.collect_health", new=AsyncMock(return_value=payload)):
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_health_unavailable_when_db_down(client):
    payload = {
        "status": "unavailable",
        "database": "down",
        "disk": {"used_percent": 50.0, "status": "ok"},
        "worker": {"status": "unknown", "stale": True},
        "environment": "development",
    }
    with patch("app.web.routes.health.collect_health", new=AsyncMock(return_value=payload)):
        response = await client.get("/health")
    assert response.status_code == 503
