"""Build golden dataset with scoring fields and manual trend labels."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import UTC, datetime
from pathlib import Path

from scripts.shadow.scoring import (
    VideoRecord,
    breakout_ratio,
    compute_channel_baselines,
    global_baseline_by_bucket,
    parse_iso_datetime,
    score_trend_cluster,
)

DATA_DIR = Path("data/shadow")
RAW_VIDEOS_PATH = DATA_DIR / "raw_videos.json"
TREND_LABELS_PATH = Path(__file__).parent / "trend_labels.json"
GOLDEN_CSV_PATH = DATA_DIR / "golden_dataset.csv"
GOLDEN_JSON_PATH = DATA_DIR / "golden_dataset.json"


def load_trend_labels(path: Path = TREND_LABELS_PATH) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["trends"]


def assign_trend(title: str, trends: list[dict]) -> dict:
    normalized = title.lower()
    best: dict | None = None
    best_hits = 0

    for trend in trends:
        if trend["trend_id"] == "trend_unlabeled":
            continue
        hits = sum(1 for kw in trend["keywords"] if kw in normalized)
        if hits > best_hits:
            best_hits = hits
            best = trend

    if best is None or best_hits == 0:
        return next(t for t in trends if t["trend_id"] == "trend_unlabeled")

    return best


def records_from_raw(raw: dict) -> list[VideoRecord]:
    records: list[VideoRecord] = []
    for row in raw["videos"]:
        records.append(
            VideoRecord(
                video_id=row["video_id"],
                channel_id=row["channel_id"],
                channel_name=row["channel_name"],
                title=row["title"],
                published_at=parse_iso_datetime(row["published_at"]),
                views=int(row["views"]),
                likes=row.get("likes"),
                comments=row.get("comments"),
                duration_seconds=int(row.get("duration_seconds", 0)),
                tier=row.get("tier", "general"),  # type: ignore[arg-type]
                url=row.get("url", ""),
            )
        )
    return records


def build_golden_dataset(
    *,
    raw_path: Path = RAW_VIDEOS_PATH,
    output_csv: Path = GOLDEN_CSV_PATH,
    output_json: Path = GOLDEN_JSON_PATH,
) -> dict:
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    trends = load_trend_labels()
    now = datetime.now(UTC)
    records = records_from_raw(raw)

    baselines = compute_channel_baselines(records, now=now)
    global_fallback = global_baseline_by_bucket(records, now=now)

    rows: list[dict] = []
    for record in records:
        scores = breakout_ratio(record, baselines, global_fallback, now=now)
        trend = assign_trend(record.title, trends)
        rows.append(
            {
                "video_id": record.video_id,
                "channel_id": record.channel_id,
                "channel_name": record.channel_name,
                "title": record.title,
                "url": record.url,
                "published_at": record.published_at.isoformat(),
                "views": record.views,
                "likes": record.likes or "",
                "comments": record.comments or "",
                "duration_seconds": record.duration_seconds,
                "tier": record.tier,
                "age_hours": scores["age_hours"],
                "age_bucket": scores["age_bucket"],
                "velocity": scores["velocity"],
                "baseline_velocity": scores["baseline_velocity"],
                "breakout_ratio": scores["breakout_ratio"],
                "capped_breakout": scores["capped_breakout"],
                "breakout_label": scores["breakout_label"],
                "baseline_confidence": scores["baseline_confidence"],
                "baseline_source": scores["baseline_source"],
                "trend_id": trend["trend_id"],
                "trend_name": trend["name"],
                "anime_title": trend.get("anime_title", ""),
                "manager_value": trend["manager_value"],
                "manager_note": trend.get("manager_note", ""),
            }
        )

    trend_clusters: dict[str, list[dict]] = {}
    for row in rows:
        trend_clusters.setdefault(row["trend_id"], []).append(row)

    trend_summaries = []
    for trend_id, members in trend_clusters.items():
        if trend_id == "trend_unlabeled":
            continue
        summary = score_trend_cluster(members, now=now)
        trend_summaries.append(
            {
                "trend_id": trend_id,
                "trend_name": members[0]["trend_name"],
                "anime_title": members[0]["anime_title"],
                "manager_value": members[0]["manager_value"],
                "video_count": len(members),
                **summary,
            }
        )

    trend_summaries.sort(key=lambda item: item["trend_score"], reverse=True)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    payload = {
        "built_at": now.isoformat(),
        "source_fetched_at": raw.get("fetched_at"),
        "video_count": len(rows),
        "channel_count": len({r["channel_id"] for r in rows}),
        "trend_count": len(trend_summaries),
        "videos": rows,
        "trend_summaries": trend_summaries,
        "channel_baselines": [
            {
                "channel_id": key[0],
                "age_bucket": key[1],
                **{k: v for k, v in value.items() if k not in {"channel_id", "age_bucket"}},
            }
            for key, value in baselines.items()
        ],
    }
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Build golden dataset from raw YouTube fetch")
    parser.add_argument("--raw", type=Path, default=RAW_VIDEOS_PATH)
    parser.add_argument("--csv", type=Path, default=GOLDEN_CSV_PATH)
    parser.add_argument("--json", type=Path, default=GOLDEN_JSON_PATH)
    args = parser.parse_args()

    payload = build_golden_dataset(
        raw_path=args.raw,
        output_csv=args.csv,
        output_json=args.json,
    )
    print(
        f"Golden dataset: {payload['video_count']} videos, "
        f"{payload['channel_count']} channels, "
        f"{payload['trend_count']} labeled trends"
    )


if __name__ == "__main__":
    main()
