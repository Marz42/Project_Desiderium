"""Normalize TikTok scrape payloads into canonical content schema."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.domain.source_confidence import SOURCE_CONFIDENCE_LOW


def _parse_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    try:
        ts = int(value)
    except (TypeError, ValueError):
        return None
    if ts > 1_000_000_000_000:
        ts //= 1000
    return datetime.fromtimestamp(ts, tz=UTC)


def _author_info(raw_item: dict[str, Any]) -> tuple[str | None, str | None]:
    author = raw_item.get("author")
    if isinstance(author, dict):
        return (
            str(author.get("id") or author.get("uniqueId") or "") or None,
            author.get("nickname") or author.get("uniqueId"),
        )
    author_id = raw_item.get("authorId")
    author_name = raw_item.get("author")
    if isinstance(author_name, str):
        return (str(author_id) if author_id else None, author_name)
    return (str(author_id) if author_id else None, None)


def _int_metric(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_tiktok_video(
    raw_item: dict[str, Any],
    *,
    selector_version: str,
    scraped_at: datetime | None = None,
) -> dict[str, Any]:
    video_id = str(raw_item.get("id", ""))
    stats = raw_item.get("stats") or {}
    if not isinstance(stats, dict):
        stats = {}
    author_id, author_name = _author_info(raw_item)
    scraped_at = scraped_at or datetime.now(UTC)

    return {
        "platform": "tiktok",
        "external_id": video_id,
        "channel_external_id": author_id,
        "channel_name": author_name,
        "title_original": (raw_item.get("desc") or "").strip() or f"TikTok {video_id}",
        "description": raw_item.get("desc"),
        "tags": _extract_hashtags(raw_item),
        "published_at": _parse_timestamp(raw_item.get("createTime")),
        "duration_seconds": _int_metric(raw_item.get("duration")),
        "url": f"https://www.tiktok.com/@{author_name or 'user'}/video/{video_id}",
        "thumbnail_url": _thumbnail_url(raw_item),
        "language": None,
        "region": None,
        "source_confidence": SOURCE_CONFIDENCE_LOW,
        "raw_payload": {
            **raw_item,
            "_meta": {
                "source_confidence": SOURCE_CONFIDENCE_LOW,
                "scraped_at": scraped_at.isoformat(),
                "selector_version": selector_version,
            },
        },
        "metrics": {
            "views": _int_metric(stats.get("playCount")) or 0,
            "likes": _int_metric(stats.get("diggCount")),
            "comments": _int_metric(stats.get("commentCount")),
            "shares": _int_metric(stats.get("shareCount")),
        },
    }


def normalize_keyword_external_id(keyword: str) -> str:
    return " ".join(keyword.strip().lower().split())


def normalize_account_external_id(value: str) -> str:
    cleaned = value.strip().lstrip("@")
    return cleaned.lower()


def _extract_hashtags(raw_item: dict[str, Any]) -> list[str]:
    text = raw_item.get("desc") or ""
    if not isinstance(text, str):
        return []
    tags: list[str] = []
    for token in text.split():
        if token.startswith("#") and len(token) > 1:
            tags.append(token[1:])
    challenges = raw_item.get("challenges") or raw_item.get("textExtra") or []
    if isinstance(challenges, list):
        for entry in challenges:
            if isinstance(entry, dict):
                name = entry.get("hashtagName") or entry.get("title")
                if name:
                    tags.append(str(name))
    return list(dict.fromkeys(tags))


def _thumbnail_url(raw_item: dict[str, Any]) -> str | None:
    video = raw_item.get("video")
    if isinstance(video, dict):
        for key in ("cover", "originCover", "dynamicCover"):
            cover = video.get(key)
            if isinstance(cover, str):
                return cover
            if isinstance(cover, list) and cover:
                first = cover[0]
                if isinstance(first, str):
                    return first
    return None
