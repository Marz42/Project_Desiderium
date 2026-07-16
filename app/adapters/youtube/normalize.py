"""Normalize YouTube API payloads into canonical content schema."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from app.domain.source_confidence import SOURCE_CONFIDENCE_HIGH


def parse_iso8601_duration(duration: str | None) -> int | None:
    if not duration:
        return None
    match = re.fullmatch(
        r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?",
        duration,
    )
    if not match:
        return None
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


def parse_published_at(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def normalize_keyword_external_id(keyword: str) -> str:
    return " ".join(keyword.strip().lower().split())


def normalize_youtube_video(raw_item: dict[str, Any]) -> dict[str, Any]:
    snippet = raw_item.get("snippet", {})
    statistics = raw_item.get("statistics", {})
    content_details = raw_item.get("contentDetails", {})
    video_id = raw_item.get("id", "")

    def _int_or_none(key: str) -> int | None:
        value = statistics.get(key)
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    return {
        "platform": "youtube",
        "external_id": video_id,
        "channel_external_id": snippet.get("channelId"),
        "channel_name": snippet.get("channelTitle"),
        "title_original": snippet.get("title", ""),
        "description": snippet.get("description"),
        "tags": snippet.get("tags") or [],
        "published_at": parse_published_at(snippet.get("publishedAt")),
        "duration_seconds": parse_iso8601_duration(content_details.get("duration")),
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "thumbnail_url": (snippet.get("thumbnails") or {}).get("high", {}).get("url"),
        "language": snippet.get("defaultAudioLanguage") or snippet.get("defaultLanguage"),
        "region": None,
        "source_confidence": SOURCE_CONFIDENCE_HIGH,
        "raw_payload": raw_item,
        "metrics": {
            "views": _int_or_none("viewCount") or 0,
            "likes": _int_or_none("likeCount"),
            "comments": _int_or_none("commentCount"),
        },
    }
