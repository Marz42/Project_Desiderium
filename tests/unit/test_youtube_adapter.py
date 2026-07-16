"""Contract tests for YouTube adapter (mocked HTTP)."""

from unittest.mock import AsyncMock, patch

import pytest

from app.adapters.youtube.adapter import YouTubeAdapter
from app.adapters.youtube.client import YouTubeClient


@pytest.fixture
def adapter():
    client = YouTubeClient("test-api-key", max_search_calls=5, daily_quota_limit=1000)
    return YouTubeAdapter(client)


@pytest.mark.asyncio
async def test_discover_channel(adapter):
    adapter._client.fetch_channel_recent_videos = AsyncMock(  # noqa: SLF001
        return_value=(["vid1", "vid2"], "next_token", {"items": []})
    )
    result = await adapter.discover_items(
        {
            "type": "channel",
            "external_id": "UCgR3SrM8T6GCFUTuxSFlR7A",
            "tier": "priority",
            "config": {},
            "known_external_ids": ["vid1"],
        }
    )
    assert result["external_ids"] == ["vid2"]
    assert result["next_cursor"] == "next_token"


@pytest.mark.asyncio
async def test_normalize_item(adapter):
    raw = {"id": "x", "snippet": {"title": "T"}, "statistics": {}, "contentDetails": {}}
    normalized = adapter.normalize_item(raw)
    assert normalized["external_id"] == "x"


@pytest.mark.asyncio
async def test_health_check(adapter):
    with patch.object(adapter._client, "_request", new=AsyncMock(return_value={"items": []})):  # noqa: SLF001
        result = await adapter.health_check()
    assert result["status"] == "ok"
