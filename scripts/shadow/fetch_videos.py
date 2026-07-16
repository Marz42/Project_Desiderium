"""Fetch recent YouTube videos for shadow validation watchlist."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.config import get_settings
from scripts.shadow.scoring import VideoRecord, parse_duration_seconds, parse_iso_datetime
from scripts.shadow.watchlist import anime_titles, channels, keywords, load_watchlist
from scripts.shadow.youtube_client import QuotaExceededError, YouTubeClient

logger = logging.getLogger(__name__)

DATA_DIR = Path("data/shadow")
RAW_VIDEOS_PATH = DATA_DIR / "raw_videos.json"
FETCH_META_PATH = DATA_DIR / "fetch_meta.json"


def raw_item_to_record(
    item: dict,
    *,
    channel_id: str,
    channel_name: str,
    tier: str,
) -> VideoRecord:
    snippet = item["snippet"]
    stats = item.get("statistics", {})
    return VideoRecord(
        video_id=item["id"],
        channel_id=channel_id,
        channel_name=channel_name,
        title=snippet.get("title", ""),
        published_at=parse_iso_datetime(snippet["publishedAt"]),
        views=int(stats.get("viewCount", 0)),
        likes=int(stats["likeCount"]) if stats.get("likeCount") else None,
        comments=int(stats["commentCount"]) if stats.get("commentCount") else None,
        duration_seconds=parse_duration_seconds(
            item.get("contentDetails", {}).get("duration", "PT0S")
        ),
        tier=tier,  # type: ignore[arg-type]
        url=f"https://www.youtube.com/watch?v={item['id']}",
    )


def fetch_all(
    *,
    videos_per_channel: int = 20,
    keyword_results: int = 12,
    output_path: Path = RAW_VIDEOS_PATH,
) -> dict:
    settings = get_settings()
    watchlist = load_watchlist()
    channel_items = channels(watchlist)
    keyword_items = keywords(watchlist) + [
        item
        for item in anime_titles(watchlist)
        if not any(k.name.lower() == item.name.lower() for k in keywords(watchlist))
    ]

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    published_after = (datetime.now(UTC) - timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%SZ")

    records: list[dict] = []
    channel_meta: list[dict] = []
    failed_channels: list[dict] = []
    discovered_ids: set[str] = set()

    with YouTubeClient(settings.youtube_api_key) as client:
        for item in channel_items:
            channel_id = client.resolve_channel_id(item.url_or_id)
            if not channel_id:
                failed_channels.append({"name": item.name, "reason": "unresolved_channel_id"})
                logger.warning("Could not resolve channel: %s", item.name)
                continue

            try:
                video_ids = client.fetch_channel_recent_videos(
                    channel_id,
                    max_videos=videos_per_channel,
                )
            except Exception as exc:  # noqa: BLE001
                failed_channels.append({"name": item.name, "reason": str(exc)})
                continue

            if not video_ids:
                failed_channels.append({"name": item.name, "reason": "no_videos"})
                continue

            details = client.get_video_details(video_ids)
            channel_meta.append(
                {
                    "name": item.name,
                    "channel_id": channel_id,
                    "tier": item.tier,
                    "video_count": len(details),
                }
            )

            for detail in details:
                if detail["id"] in discovered_ids:
                    continue
                discovered_ids.add(detail["id"])
                record = raw_item_to_record(
                    detail,
                    channel_id=channel_id,
                    channel_name=item.name,
                    tier=item.tier,
                )
                records.append(
                    {
                        "video_id": record.video_id,
                        "channel_id": record.channel_id,
                        "channel_name": record.channel_name,
                        "title": record.title,
                        "published_at": record.published_at.isoformat(),
                        "views": record.views,
                        "likes": record.likes,
                        "comments": record.comments,
                        "duration_seconds": record.duration_seconds,
                        "tier": record.tier,
                        "url": record.url,
                        "source": "channel_uploads",
                    }
                )

        keyword_meta: list[dict] = []
        for item in keyword_items:
            try:
                if item.type == "keyword":
                    query = item.name
                else:
                    query = item.url_or_id or f"{item.name} recap"
                video_ids = client.search_videos(
                    query,
                    max_results=keyword_results,
                    published_after=published_after,
                )
            except QuotaExceededError:
                logger.warning("Search quota exhausted; stopping keyword discovery")
                break
            except Exception as exc:  # noqa: BLE001
                keyword_meta.append({"keyword": item.name, "error": str(exc)})
                continue

            details = client.get_video_details(video_ids)
            keyword_meta.append({"keyword": item.name, "video_count": len(details)})

            for detail in details:
                if detail["id"] in discovered_ids:
                    continue
                discovered_ids.add(detail["id"])
                snippet = detail["snippet"]
                record = raw_item_to_record(
                    detail,
                    channel_id=snippet.get("channelId", ""),
                    channel_name=snippet.get("channelTitle", ""),
                    tier=item.tier,
                )
                records.append(
                    {
                        "video_id": record.video_id,
                        "channel_id": record.channel_id,
                        "channel_name": record.channel_name,
                        "title": record.title,
                        "published_at": record.published_at.isoformat(),
                        "views": record.views,
                        "likes": record.likes,
                        "comments": record.comments,
                        "duration_seconds": record.duration_seconds,
                        "tier": record.tier,
                        "url": record.url,
                        "source": f"keyword:{item.name}",
                    }
                )

        quota = client.quota_summary()

    payload = {
        "fetched_at": datetime.now(UTC).isoformat(),
        "video_count": len(records),
        "channel_count": len({r["channel_id"] for r in records}),
        "quota": quota,
        "channels": channel_meta,
        "keywords": keyword_meta,
        "failed_channels": failed_channels,
        "videos": records,
    }

    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    FETCH_META_PATH.write_text(
        json.dumps(
            {
                "fetched_at": payload["fetched_at"],
                "video_count": payload["video_count"],
                "channel_count": payload["channel_count"],
                "quota": quota,
                "failed_channels": failed_channels,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return payload


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Fetch YouTube videos for shadow validation")
    parser.add_argument("--videos-per-channel", type=int, default=20)
    parser.add_argument("--keyword-results", type=int, default=12)
    parser.add_argument("--output", type=Path, default=RAW_VIDEOS_PATH)
    args = parser.parse_args()

    payload = fetch_all(
        videos_per_channel=args.videos_per_channel,
        keyword_results=args.keyword_results,
        output_path=args.output,
    )
    print(
        f"Fetched {payload['video_count']} videos from "
        f"{payload['channel_count']} channels. "
        f"Quota estimate: {payload['quota']['quota_used_estimate']}"
    )


if __name__ == "__main__":
    main()
