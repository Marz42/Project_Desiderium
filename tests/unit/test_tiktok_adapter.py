"""Contract tests for TikTok adapter (mocked HTTP)."""

from unittest.mock import AsyncMock, patch

import pytest

from app.adapters.tiktok.adapter import TikTokAdapter
from app.adapters.tiktok.client import TikTokClient
from app.adapters.tiktok.errors import CookieExpiredError
from app.domain.source_confidence import SOURCE_CONFIDENCE_LOW

SAMPLE_HTML = """
<html><body>
<script id="SIGI_STATE" type="application/json">
{"ItemModule":{"7123456789012345678":{"id":"7123456789012345678","desc":"#anime test","createTime":1710000000,
"author":{"id":"user1","uniqueId":"creator","nickname":"Creator"},
"stats":{"playCount":1000,"diggCount":50,"commentCount":5,"shareCount":2},
"video":{"cover":"https://example.com/cover.jpg"},"duration":15}}}
</script></body></html>
"""


@pytest.fixture
def adapter():
    client = TikTokClient("sessionid=test; tt_chain_token=abc", page_version="v1")
    return TikTokAdapter(client, enabled=True, page_version="v1")


@pytest.mark.asyncio
async def test_discover_account(adapter):
    with patch.object(
        adapter._client._client,  # noqa: SLF001
        "get",
        new=AsyncMock(
            return_value=type(
                "Resp",
                (),
                {"status_code": 200, "text": SAMPLE_HTML, "url": "https://www.tiktok.com/@creator"},
            )()
        ),
    ):
        result = await adapter.discover_items(
            {
                "type": "account",
                "external_id": "@creator",
                "tier": "experimental",
                "config": {},
                "known_external_ids": [],
            }
        )
    assert result["external_ids"] == ["7123456789012345678"]
    assert len(result["raw_videos"]) == 1


@pytest.mark.asyncio
async def test_normalize_item(adapter):
    raw = {
        "id": "7123456789012345678",
        "desc": "hello",
        "createTime": 1710000000,
        "author": {"id": "u1", "uniqueId": "creator"},
        "stats": {"playCount": 10},
    }
    normalized = adapter.normalize_item(raw)
    assert normalized["external_id"] == "7123456789012345678"
    assert normalized["source_confidence"] == SOURCE_CONFIDENCE_LOW
    assert normalized["raw_payload"]["_meta"]["selector_version"] == "v1"


@pytest.mark.asyncio
async def test_cookie_expired(adapter):
    with patch.object(
        adapter._client._client,  # noqa: SLF001
        "get",
        new=AsyncMock(
            return_value=type(
                "Resp",
                (),
                {
                    "status_code": 200,
                    "text": "<html>login-modal please log in</html>",
                    "url": "https://www.tiktok.com/login",
                },
            )()
        ),
    ):
        result = await adapter.discover_items(
            {"type": "account", "external_id": "creator", "tier": "general", "config": {}}
        )
    assert result.get("cookie_expired") is True
    assert adapter.cookie_expired is True


@pytest.mark.asyncio
async def test_health_check_disabled():
    client = TikTokClient("sessionid=test", page_version="v1")
    adapter = TikTokAdapter(client, enabled=False)
    result = await adapter.health_check()
    assert result["status"] == "disabled"


def test_client_requires_cookie():
    with pytest.raises(CookieExpiredError):
        TikTokClient("")
