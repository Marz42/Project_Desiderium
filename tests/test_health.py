from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_health_live(client):
    response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_ready_when_database_up(client):
    with patch("app.web.routes.health.check_database_connection", new=AsyncMock(return_value=True)):
        response = await client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "up"}


@pytest.mark.asyncio
async def test_health_ready_when_database_down(client):
    with patch("app.web.routes.health.check_database_connection", new=AsyncMock(return_value=False)):
        response = await client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "down"}
