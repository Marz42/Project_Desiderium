"""Minimal YouTube Data API v3 client with file cache and quota tracking."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)

API_BASE = "https://www.googleapis.com/youtube/v3"
DEFAULT_CACHE_DIR = Path("data/shadow/cache")
MAX_SEARCH_CALLS = 10
BATCH_SIZE = 50

# Quota costs per YouTube Data API v3 reference
QUOTA_COSTS = {
    "channels.list": 1,
    "playlistItems.list": 1,
    "videos.list": 1,
    "search.list": 100,
}


class QuotaExceededError(RuntimeError):
    pass


class YouTubeClient:
    def __init__(
        self,
        api_key: str,
        cache_dir: Path | None = None,
        max_search_calls: int = MAX_SEARCH_CALLS,
    ) -> None:
        if not api_key:
            raise ValueError("YouTube API key is required")
        self.api_key = api_key
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_search_calls = max_search_calls
        self.search_calls = 0
        self.quota_used = 0
        self._client = httpx.Client(timeout=30.0)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> YouTubeClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _cache_key(self, endpoint: str, params: dict[str, Any]) -> str:
        payload = json.dumps({"endpoint": endpoint, "params": params}, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

    def _read_cache(self, key: str) -> dict[str, Any] | None:
        path = self.cache_dir / f"{key}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        cached_at = datetime.fromisoformat(data["cached_at"])
        if (datetime.now(UTC) - cached_at).total_seconds() > 86400:
            return None
        return data["response"]

    def _write_cache(self, key: str, response: dict[str, Any]) -> None:
        path = self.cache_dir / f"{key}.json"
        path.write_text(
            json.dumps(
                {"cached_at": datetime.now(UTC).isoformat(), "response": response},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def _request(
        self, endpoint: str, params: dict[str, Any], *, use_cache: bool = True
    ) -> dict[str, Any]:
        if endpoint == "search":
            if self.search_calls >= self.max_search_calls:
                raise QuotaExceededError(
                    f"search.list budget exhausted ({self.max_search_calls} calls)"
                )
            self.search_calls += 1

        cost = QUOTA_COSTS.get(f"{endpoint}.list", 1)
        self.quota_used += cost

        request_params = {**params, "key": self.api_key}
        cache_key = self._cache_key(endpoint, request_params)
        if use_cache:
            cached = self._read_cache(cache_key)
            if cached is not None:
                logger.debug("cache hit %s", endpoint)
                return cached

        url = f"{API_BASE}/{endpoint}?{urlencode(request_params)}"
        for attempt in range(4):
            response = self._client.get(url)
            if response.status_code == 403 and "quota" in response.text.lower():
                raise QuotaExceededError(response.text)
            if response.status_code in {429, 500, 502, 503}:
                time.sleep(2**attempt)
                continue
            response.raise_for_status()
            data = response.json()
            if use_cache:
                self._write_cache(cache_key, data)
            return data

        response.raise_for_status()
        return {}

    def resolve_channel_id(self, url_or_id: str) -> str | None:
        """Resolve a channel ID from UC id, @handle, or channel URL."""
        value = url_or_id.strip()
        if value.startswith("UC") and len(value) == 24:
            data = self._request(
                "channels",
                {"part": "id", "id": value},
            )
            items = data.get("items", [])
            if items:
                return items[0]["id"]
            return None

        handle = value
        if "youtube.com/" in value:
            if "/channel/" in value:
                return self.resolve_channel_id(
                    value.split("/channel/")[1].split("/")[0].split("?")[0]
                )
            if "/@" in value:
                handle = value.split("/@")[1].split("/")[0].split("?")[0]

        if handle.startswith("@"):
            handle = handle[1:]

        data = self._request(
            "channels",
            {"part": "id", "forHandle": handle},
        )
        items = data.get("items", [])
        return items[0]["id"] if items else None

    def get_uploads_playlist_id(self, channel_id: str) -> str | None:
        data = self._request(
            "channels",
            {"part": "contentDetails", "id": channel_id},
        )
        items = data.get("items", [])
        if not items:
            return None
        return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

    def list_playlist_videos(
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
        return self._request("playlistItems", params)

    def fetch_channel_recent_videos(
        self,
        channel_id: str,
        *,
        max_videos: int = 25,
    ) -> list[str]:
        playlist_id = self.get_uploads_playlist_id(channel_id)
        if not playlist_id:
            return []

        video_ids: list[str] = []
        page_token: str | None = None
        while len(video_ids) < max_videos:
            batch_size = min(50, max_videos - len(video_ids))
            data = self.list_playlist_videos(
                playlist_id,
                max_results=batch_size,
                page_token=page_token,
            )
            for item in data.get("items", []):
                vid = item.get("contentDetails", {}).get("videoId")
                if vid:
                    video_ids.append(vid)
            page_token = data.get("nextPageToken")
            if not page_token:
                break
        return video_ids[:max_videos]

    def search_videos(
        self,
        query: str,
        *,
        max_results: int = 15,
        published_after: str | None = None,
    ) -> list[str]:
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

        data = self._request("search", params, use_cache=False)
        return [
            item["id"]["videoId"]
            for item in data.get("items", [])
            if item.get("id", {}).get("videoId")
        ]

    def get_video_details(self, video_ids: list[str]) -> list[dict[str, Any]]:
        if not video_ids:
            return []

        results: list[dict[str, Any]] = []
        for i in range(0, len(video_ids), BATCH_SIZE):
            batch = video_ids[i : i + BATCH_SIZE]
            data = self._request(
                "videos",
                {
                    "part": "snippet,statistics,contentDetails",
                    "id": ",".join(batch),
                },
            )
            results.extend(data.get("items", []))
        return results

    def quota_summary(self) -> dict[str, int]:
        return {
            "quota_used_estimate": self.quota_used,
            "search_calls": self.search_calls,
            "max_search_calls": self.max_search_calls,
        }
