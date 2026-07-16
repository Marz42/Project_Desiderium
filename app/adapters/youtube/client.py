"""Async YouTube Data API v3 client with quota tracking and exponential backoff."""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)

API_BASE = "https://www.googleapis.com/youtube/v3"
BATCH_SIZE = 50

QUOTA_COSTS = {
    "channels.list": 1,
    "playlistItems.list": 1,
    "videos.list": 1,
    "search.list": 100,
}


class QuotaExceededError(RuntimeError):
    """Raised when YouTube API quota or search budget is exhausted."""


class YouTubeAPIError(RuntimeError):
    """Raised for non-retryable YouTube API failures."""


class YouTubeClient:
    def __init__(
        self,
        api_key: str,
        *,
        max_search_calls: int = 100,
        daily_quota_limit: int = 10_000,
        timeout: float = 30.0,
    ) -> None:
        if not api_key:
            raise ValueError("YouTube API key is required")
        self.api_key = api_key
        self.max_search_calls = max_search_calls
        self.daily_quota_limit = daily_quota_limit
        self.search_calls = 0
        self.quota_used = 0
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> YouTubeClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    def _check_quota(self, cost: int) -> None:
        if self.quota_used + cost > self.daily_quota_limit:
            raise QuotaExceededError(
                f"daily quota budget exhausted ({self.quota_used}/{self.daily_quota_limit})"
            )

    async def _request(
        self,
        endpoint: str,
        params: dict[str, Any],
        *,
        use_cache: bool = True,  # noqa: ARG002 - reserved for future disk cache
    ) -> dict[str, Any]:
        if endpoint == "search":
            if self.search_calls >= self.max_search_calls:
                raise QuotaExceededError(
                    f"search.list budget exhausted ({self.max_search_calls} calls)"
                )
            self.search_calls += 1

        cost = QUOTA_COSTS.get(f"{endpoint}.list", 1)
        self._check_quota(cost)
        self.quota_used += cost

        request_params = {**params, "key": self.api_key}
        url = f"{API_BASE}/{endpoint}?{urlencode(request_params)}"

        last_response: httpx.Response | None = None
        for attempt in range(4):
            response = await self._client.get(url)
            last_response = response
            if response.status_code == 403:
                body = response.text.lower()
                if "quota" in body or "quotaexceeded" in body:
                    raise QuotaExceededError(response.text)
                raise YouTubeAPIError(response.text)
            if response.status_code in {429, 500, 502, 503}:
                await asyncio.sleep(2**attempt)
                continue
            response.raise_for_status()
            return response.json()

        if last_response is not None:
            last_response.raise_for_status()
        return {}

    async def resolve_channel_id(self, url_or_id: str) -> str | None:
        """Resolve a channel ID from UC id, @handle, or channel URL."""
        value = url_or_id.strip()
        if value.startswith("UC") and len(value) == 24:
            data = await self._request("channels", {"part": "id", "id": value})
            items = data.get("items", [])
            return items[0]["id"] if items else None

        handle = value
        if "youtube.com/" in value:
            if "/channel/" in value:
                channel_part = value.split("/channel/")[1].split("/")[0].split("?")[0]
                return await self.resolve_channel_id(channel_part)
            if "/@" in value:
                handle = value.split("/@")[1].split("/")[0].split("?")[0]

        if handle.startswith("@"):
            handle = handle[1:]

        data = await self._request("channels", {"part": "id", "forHandle": handle})
        items = data.get("items", [])
        return items[0]["id"] if items else None

    async def get_uploads_playlist_id(self, channel_id: str) -> str | None:
        data = await self._request("channels", {"part": "contentDetails", "id": channel_id})
        items = data.get("items", [])
        if not items:
            return None
        return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

    async def list_playlist_videos(
        self,
        playlist_id: str,
        *,
        max_results: int = 50,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "part": "snippet,contentDetails",
            "playlistId": playlist_id,
            "maxResults": min(max_results, 50),
        }
        if page_token:
            params["pageToken"] = page_token
        return await self._request("playlistItems", params)

    async def fetch_channel_recent_videos(
        self,
        channel_id: str,
        *,
        max_videos: int = 25,
        page_token: str | None = None,
    ) -> tuple[list[str], str | None, dict[str, Any]]:
        """Return video IDs, next page token, and the raw playlist response."""
        playlist_id = await self.get_uploads_playlist_id(channel_id)
        if not playlist_id:
            return [], None, {}

        video_ids: list[str] = []
        current_token = page_token
        last_raw: dict[str, Any] = {}
        while len(video_ids) < max_videos:
            batch_size = min(50, max_videos - len(video_ids))
            data = await self.list_playlist_videos(
                playlist_id,
                max_results=batch_size,
                page_token=current_token,
            )
            last_raw = data
            for item in data.get("items", []):
                vid = item.get("contentDetails", {}).get("videoId")
                if vid:
                    video_ids.append(vid)
            current_token = data.get("nextPageToken")
            if not current_token:
                break
        return video_ids[:max_videos], current_token, last_raw

    async def search_videos(
        self,
        query: str,
        *,
        max_results: int = 15,
        published_after: str | None = None,
        page_token: str | None = None,
    ) -> tuple[list[str], str | None, dict[str, Any]]:
        params: dict[str, Any] = {
            "part": "snippet",
            "type": "video",
            "q": query,
            "maxResults": min(max_results, 50),
            "order": "date",
            "relevanceLanguage": "en",
        }
        if published_after:
            params["publishedAfter"] = published_after
        if page_token:
            params["pageToken"] = page_token

        data = await self._request("search", params, use_cache=False)
        video_ids = [
            item["id"]["videoId"]
            for item in data.get("items", [])
            if item.get("id", {}).get("videoId")
        ]
        return video_ids, data.get("nextPageToken"), data

    async def get_video_details(self, video_ids: list[str]) -> list[dict[str, Any]]:
        if not video_ids:
            return []

        results: list[dict[str, Any]] = []
        for i in range(0, len(video_ids), BATCH_SIZE):
            batch = video_ids[i : i + BATCH_SIZE]
            data = await self._request(
                "videos",
                {
                    "part": "snippet,statistics,contentDetails",
                    "id": ",".join(batch),
                },
            )
            results.extend(data.get("items", []))
        return results

    async def health_check(self) -> dict[str, Any]:
        try:
            await self._request("channels", {"part": "id", "id": "UC_x5XG1OV2P6uZZ5FSM9Ttw"})
            return {"status": "ok", "quota_used": self.quota_used}
        except QuotaExceededError as exc:
            return {"status": "quota_exceeded", "error": str(exc)}
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "error": str(exc)}

    def quota_summary(self) -> dict[str, int]:
        return {
            "quota_used_estimate": self.quota_used,
            "search_calls": self.search_calls,
            "max_search_calls": self.max_search_calls,
            "daily_quota_limit": self.daily_quota_limit,
        }
