"""YouTube SourceAdapter implementation."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from app.adapters.youtube.client import QuotaExceededError, YouTubeClient
from app.adapters.youtube.normalize import (
    normalize_keyword_external_id,
    normalize_youtube_video,
)
from app.models import WatchItemType

logger = logging.getLogger(__name__)

DEFAULT_MAX_VIDEOS = {
    "priority": 25,
    "general": 15,
    "experimental": 10,
}


class YouTubeAdapter:
    """Implements SourceAdapter for YouTube Data API v3."""

    adapter_name = "youtube"

    def __init__(self, client: YouTubeClient) -> None:
        self._client = client
        self._quota_exhausted = False

    @property
    def quota_exhausted(self) -> bool:
        return self._quota_exhausted

    async def close(self) -> None:
        await self._client.close()

    async def discover_items(
        self,
        watch_item: dict[str, Any],
        cursor: str | None = None,
    ) -> dict[str, Any]:
        item_type = watch_item.get("type", "")
        tier = watch_item.get("tier", "general")
        config = watch_item.get("config") or {}
        max_videos = config.get("max_videos") or DEFAULT_MAX_VIDEOS.get(tier, 15)
        raw_responses: list[dict[str, Any]] = []

        try:
            if item_type in (WatchItemType.CHANNEL.value, "channel"):
                return await self._discover_channel(
                    watch_item,
                    cursor=cursor,
                    max_videos=max_videos,
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
                    cursor=cursor,
                    max_videos=max_videos,
                    raw_responses=raw_responses,
                )
            return {
                "external_ids": [],
                "next_cursor": None,
                "raw_responses": raw_responses,
                "error": f"unsupported watch item type: {item_type}",
            }
        except QuotaExceededError as exc:
            self._quota_exhausted = True
            logger.warning("YouTube quota exhausted during discover: %s", exc)
            return {
                "external_ids": [],
                "next_cursor": cursor,
                "raw_responses": raw_responses,
                "error": str(exc),
                "quota_exhausted": True,
            }

    async def _discover_channel(
        self,
        watch_item: dict[str, Any],
        *,
        cursor: str | None,
        max_videos: int,
        raw_responses: list[dict[str, Any]],
    ) -> dict[str, Any]:
        channel_id = watch_item.get("external_id") or ""
        if not channel_id.startswith("UC"):
            resolved = await self._client.resolve_channel_id(watch_item.get("url") or channel_id)
            if not resolved:
                return {
                    "external_ids": [],
                    "next_cursor": None,
                    "raw_responses": raw_responses,
                    "error": "could not resolve channel id",
                }
            channel_id = resolved

        page_token = cursor or (watch_item.get("config") or {}).get("page_token")
        video_ids, next_token, raw = await self._client.fetch_channel_recent_videos(
            channel_id,
            max_videos=max_videos,
            page_token=page_token,
        )
        if raw:
            raw_responses.append(raw)

        known_ids = set(watch_item.get("known_external_ids") or [])
        new_ids = [vid for vid in video_ids if vid not in known_ids]

        return {
            "external_ids": new_ids,
            "all_fetched_ids": video_ids,
            "next_cursor": next_token,
            "raw_responses": raw_responses,
            "resolved_channel_id": channel_id,
        }

    async def _discover_keyword(
        self,
        watch_item: dict[str, Any],
        *,
        cursor: str | None,
        max_videos: int,
        raw_responses: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if self._quota_exhausted:
            return {
                "external_ids": [],
                "next_cursor": cursor,
                "raw_responses": raw_responses,
                "error": "search skipped: quota exhausted",
                "quota_exhausted": True,
            }

        config = watch_item.get("config") or {}
        query = watch_item.get("external_id") or watch_item.get("name", "")
        hours_back = config.get("search_hours_back", 72)
        published_after = (datetime.now(UTC) - timedelta(hours=hours_back)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

        video_ids, next_token, raw = await self._client.search_videos(
            query,
            max_results=min(max_videos, 25),
            published_after=published_after,
            page_token=cursor,
        )
        raw_responses.append(raw)

        known_ids = set(watch_item.get("known_external_ids") or [])
        new_ids = [vid for vid in video_ids if vid not in known_ids]

        return {
            "external_ids": new_ids,
            "all_fetched_ids": video_ids,
            "next_cursor": next_token,
            "raw_responses": raw_responses,
        }

    async def fetch_item_details(self, external_ids: list[str]) -> list[dict[str, Any]]:
        if not external_ids:
            return []
        try:
            return await self._client.get_video_details(external_ids)
        except QuotaExceededError:
            self._quota_exhausted = True
            raise

    async def fetch_metrics(self, external_ids: list[str]) -> list[dict[str, Any]]:
        items = await self.fetch_item_details(external_ids)
        return [
            {
                "external_id": item.get("id"),
                "metrics": normalize_youtube_video(item).get("metrics", {}),
                "raw_payload": item,
            }
            for item in items
        ]

    def normalize_item(self, raw_item: dict[str, Any]) -> dict[str, Any]:
        return normalize_youtube_video(raw_item)

    async def health_check(self) -> dict[str, Any]:
        result = await self._client.health_check()
        result["quota_summary"] = self._client.quota_summary()
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
        if url_or_id.startswith("UC") and len(url_or_id) == 24:
            return url_or_id
        resolved = await self._client.resolve_channel_id(url_or_id or name)
        if not resolved:
            raise ValueError(f"could not resolve channel id for: {url_or_id or name}")
        return resolved

    def quota_summary(self) -> dict[str, int]:
        return self._client.quota_summary()
