"""TikTok SourceAdapter implementation (experimental)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.adapters.tiktok.client import TikTokClient
from app.adapters.tiktok.errors import CookieExpiredError, TikTokDisabledError, TikTokScrapeError
from app.adapters.tiktok.normalize import (
    normalize_account_external_id,
    normalize_keyword_external_id,
    normalize_tiktok_video,
)
from app.models import WatchItemType

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TIKTOK_CONFIG_PATH = PROJECT_ROOT / "config" / "tiktok.yaml"

DEFAULT_MAX_ITEMS = {
    "priority": 20,
    "general": 15,
    "experimental": 10,
}


@lru_cache
def get_tiktok_config() -> dict[str, Any]:
    if not DEFAULT_TIKTOK_CONFIG_PATH.exists():
        return {"page_version": "v1", "default_max_items": DEFAULT_MAX_ITEMS}
    raw = yaml.safe_load(DEFAULT_TIKTOK_CONFIG_PATH.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


class TikTokAdapter:
    """Implements SourceAdapter for experimental TikTok web scraping."""

    adapter_name = "tiktok"

    def __init__(
        self,
        client: TikTokClient,
        *,
        enabled: bool = True,
        page_version: str | None = None,
    ) -> None:
        self._client = client
        self._enabled = enabled
        self._config = get_tiktok_config()
        self._page_version = page_version or str(self._config.get("page_version", "v1"))
        self._cookie_expired = False
        self._consecutive_failures = 0

    @property
    def cookie_expired(self) -> bool:
        return self._cookie_expired

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures

    def _ensure_enabled(self) -> None:
        if not self._enabled:
            raise TikTokDisabledError("TikTok adapter is disabled (TIKTOK_ENABLED=false)")

    async def close(self) -> None:
        await self._client.close()

    async def discover_items(
        self,
        watch_item: dict[str, Any],
        cursor: str | None = None,
    ) -> dict[str, Any]:
        self._ensure_enabled()
        item_type = watch_item.get("type", "")
        tier = watch_item.get("tier", "general")
        config = watch_item.get("config") or {}
        max_items = config.get("max_items") or DEFAULT_MAX_ITEMS.get(tier, 15)
        raw_responses: list[dict[str, Any]] = []
        page_cursor = cursor or config.get("page_token")

        try:
            if item_type in (WatchItemType.ACCOUNT.value, "account"):
                return await self._discover_account(
                    watch_item,
                    cursor=page_cursor,
                    max_items=max_items,
                    raw_responses=raw_responses,
                )
            if item_type in (
                WatchItemType.KEYWORD.value,
                WatchItemType.ANIME.value,
                "keyword",
                "anime",
            ):
                return await self._discover_keyword(
                    watch_item,
                    cursor=page_cursor,
                    max_items=max_items,
                    raw_responses=raw_responses,
                )
            if item_type in (WatchItemType.RANKING.value, "ranking"):
                return await self._discover_ranking(
                    watch_item,
                    cursor=page_cursor,
                    max_items=max_items,
                    raw_responses=raw_responses,
                )
            return {
                "external_ids": [],
                "next_cursor": None,
                "raw_responses": raw_responses,
                "error": f"unsupported TikTok watch item type: {item_type}",
            }
        except CookieExpiredError as exc:
            self._cookie_expired = True
            self._record_failure(exc)
            return {
                "external_ids": [],
                "next_cursor": page_cursor,
                "raw_responses": raw_responses,
                "error": str(exc),
                "cookie_expired": True,
            }
        except TikTokScrapeError as exc:
            self._record_failure(exc)
            return {
                "external_ids": [],
                "next_cursor": page_cursor,
                "raw_responses": raw_responses,
                "error": str(exc),
            }

    async def _discover_account(
        self,
        watch_item: dict[str, Any],
        *,
        cursor: str | None,
        max_items: int,
        raw_responses: list[dict[str, Any]],
    ) -> dict[str, Any]:
        username = normalize_account_external_id(
            watch_item.get("external_id") or watch_item.get("url") or watch_item.get("name", "")
        )
        page = await self._client.fetch_account_videos(username, max_items=max_items, cursor=cursor)
        raw_responses.append({"url": page.url, "state_keys": list(page.raw_state.keys())})
        return self._build_discover_result(page, watch_item, raw_responses)

    async def _discover_keyword(
        self,
        watch_item: dict[str, Any],
        *,
        cursor: str | None,
        max_items: int,
        raw_responses: list[dict[str, Any]],
    ) -> dict[str, Any]:
        query = watch_item.get("external_id") or watch_item.get("name", "")
        page = await self._client.fetch_keyword_videos(query, max_items=max_items, cursor=cursor)
        raw_responses.append({"url": page.url, "state_keys": list(page.raw_state.keys())})
        return self._build_discover_result(page, watch_item, raw_responses)

    async def _discover_ranking(
        self,
        watch_item: dict[str, Any],
        *,
        cursor: str | None,
        max_items: int,
        raw_responses: list[dict[str, Any]],
    ) -> dict[str, Any]:
        config = watch_item.get("config") or {}
        list_url = config.get("list_url") or watch_item.get("url")
        tag = config.get("tag") or watch_item.get("external_id")
        if list_url:
            page = await self._client.fetch_list_url(list_url, max_items=max_items, cursor=cursor)
        elif tag:
            page = await self._client.fetch_tag_videos(tag, max_items=max_items, cursor=cursor)
        else:
            return {
                "external_ids": [],
                "next_cursor": None,
                "raw_responses": raw_responses,
                "error": "ranking watch item requires config.list_url or config.tag",
            }
        raw_responses.append({"url": page.url, "state_keys": list(page.raw_state.keys())})
        return self._build_discover_result(page, watch_item, raw_responses)

    def _build_discover_result(
        self,
        page: Any,
        watch_item: dict[str, Any],
        raw_responses: list[dict[str, Any]],
    ) -> dict[str, Any]:
        self._consecutive_failures = 0
        video_ids = [str(v.get("id", "")) for v in page.videos if v.get("id")]
        known_ids = set(watch_item.get("known_external_ids") or [])
        new_ids = [vid for vid in video_ids if vid not in known_ids]
        return {
            "external_ids": new_ids,
            "all_fetched_ids": video_ids,
            "next_cursor": page.next_cursor,
            "raw_responses": raw_responses,
            "raw_videos": page.videos,
        }

    async def fetch_item_details(self, external_ids: list[str]) -> list[dict[str, Any]]:
        self._ensure_enabled()
        if not external_ids:
            return []
        cached = getattr(self, "_last_discovered_videos", {})
        results: list[dict[str, Any]] = []
        for ext_id in external_ids:
            if ext_id in cached:
                results.append(cached[ext_id])
        return results

    async def fetch_metrics(self, external_ids: list[str]) -> list[dict[str, Any]]:
        items = await self.fetch_item_details(external_ids)
        return [
            {
                "external_id": item.get("id"),
                "metrics": normalize_tiktok_video(
                    item,
                    selector_version=self._page_version,
                ).get("metrics", {}),
                "raw_payload": item,
            }
            for item in items
        ]

    def normalize_item(self, raw_item: dict[str, Any]) -> dict[str, Any]:
        return normalize_tiktok_video(raw_item, selector_version=self._page_version)

    async def health_check(self) -> dict[str, Any]:
        if not self._enabled:
            return {
                "status": "disabled",
                "adapter": "tiktok",
                "enabled": False,
            }
        result = await self._client.health_check()
        result["enabled"] = True
        result["consecutive_failures"] = self._consecutive_failures
        return result

    async def resolve_external_id(
        self,
        item_type: str,
        url_or_id: str,
        name: str,
    ) -> str:
        if item_type in (
            WatchItemType.KEYWORD.value,
            WatchItemType.ANIME.value,
            "keyword",
            "anime",
        ):
            return normalize_keyword_external_id(url_or_id or name)
        if item_type in (WatchItemType.RANKING.value, "ranking"):
            return normalize_keyword_external_id(url_or_id or name)
        return normalize_account_external_id(url_or_id or name)

    def cache_discovered_videos(self, videos: list[dict[str, Any]]) -> None:
        self._last_discovered_videos = {str(v.get("id", "")): v for v in videos if v.get("id")}

    def _record_failure(self, exc: Exception) -> None:
        self._consecutive_failures += 1
        threshold = int(self._config.get("failure_alert_threshold", 3))
        log_fn = logger.error if self._consecutive_failures >= threshold else logger.warning
        log_fn(
            "TikTok adapter failure (%s/%s): %s",
            self._consecutive_failures,
            threshold,
            exc,
            extra={
                "service": "tiktok",
                "component": "adapter",
                "alert": self._consecutive_failures >= threshold,
                "failure_count": self._consecutive_failures,
                "scraped_at": datetime.now(UTC).isoformat(),
            },
        )
