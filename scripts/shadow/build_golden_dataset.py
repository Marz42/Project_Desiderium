"""Build golden dataset with scoring fields and production clustering path."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import UTC, datetime
from pathlib import Path

from app.domain.trend_metrics import parse_iso_datetime
from app.services.clustering import assignments_to_member_rows, cluster_videos
from app.services.relevance import classify_relevance
from app.services.scoring import TrendScoringService
from app.services.scoring_config import get_scoring_config
from scripts.shadow.scoring import (
    VideoRecord,
    breakout_ratio,
    compute_channel_baselines,
    global_baseline_by_bucket,
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
                language=row.get("language"),
                tier=row.get("tier", "general"),
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
    now = parse_iso_datetime(raw["fetched_at"]) if raw.get("fetched_at") else datetime.now(UTC)
    records = records_from_raw(raw)
    scoring = TrendScoringService(get_scoring_config())

    baselines = compute_channel_baselines(records, now=now)
    global_fallback = global_baseline_by_bucket(records, now=now)

    rows: list[dict] = []
    config = get_scoring_config()
    for record in records:
        relevance = classify_relevance(
            title=record.title,
            language=record.language,
            config=config.relevance,
        )
        if relevance.multiplier <= 0:
            continue
        scores = breakout_ratio(record, baselines, global_fallback, now=now)
        trend = assign_trend(record.title, trends)
        rows.append(
            {
                "content_item_id": record.video_id,
                "video_id": record.video_id,
                "channel_id": record.channel_id,
                "channel_name": record.channel_name,
                "title": record.title,
                "title_original": record.title,
                "url": record.url,
                "published_at": record.published_at.isoformat(),
                "views": record.views,
                "likes": record.likes or "",
                "comments": record.comments or "",
                "duration_seconds": record.duration_seconds,
                "language": record.language or "",
                "tier": record.tier,
                "relevance_category": relevance.category,
                "relevance_multiplier": relevance.multiplier,
                "age_hours": scores["age_hours"],
                "age_bucket": scores["age_bucket"],
                "velocity": scores["velocity"],
                "baseline_velocity": scores["baseline_velocity"],
                "breakout_ratio": scores["breakout_ratio"],
                "capped_breakout": scores["capped_breakout"],
                "breakout_label": scores["breakout_label"],
                "baseline_confidence": scores["baseline_confidence"],
                "baseline_source": scores["baseline_source"],
                "label_trend_id": trend["trend_id"],
                "trend_id": trend["trend_id"],
                "trend_name": trend["name"],
                "anime_title": trend.get("anime_title", ""),
                "manager_value": trend["manager_value"],
                "manager_note": trend.get("manager_note", ""),
            }
        )

    # Production clustering path (entity dictionary), scored with TrendScoringService.
    production_clusters = cluster_videos(rows)
    video_lookup = {row["content_item_id"]: row for row in rows}
    production_summaries = []
    for entity_id, assignments in production_clusters.items():
        members = assignments_to_member_rows(assignments, video_lookup)
        summary = scoring.score_cluster(members)
        label_values = [video_lookup[a.content_item_id].get("manager_value") for a in assignments]
        high_share = label_values.count("high") / max(len(label_values), 1)
        manager_value = (
            "high" if high_share >= 0.5 else ("low" if "low" in label_values else "normal")
        )
        production_summaries.append(
            {
                "trend_id": entity_id,
                "trend_name": assignments[0].canonical_name,
                "anime_title": assignments[0].anime_title,
                "manager_value": manager_value,
                "video_count": len(members),
                "source": "production_cluster_videos",
                **summary,
            }
        )
    production_summaries.sort(key=lambda item: item["trend_score"], reverse=True)

    # Keep labeled summaries for manager-value precision checks.
    trend_clusters: dict[str, list[dict]] = {}
    for row in rows:
        trend_clusters.setdefault(row["label_trend_id"], []).append(row)

    labeled_summaries = []
    for trend_id, members in trend_clusters.items():
        if trend_id == "trend_unlabeled":
            continue
        summary = scoring.score_cluster(members)
        labeled_summaries.append(
            {
                "trend_id": trend_id,
                "trend_name": members[0]["trend_name"],
                "anime_title": members[0]["anime_title"],
                "manager_value": members[0]["manager_value"],
                "video_count": len(members),
                "source": "manager_labels",
                **summary,
            }
        )
    labeled_summaries.sort(key=lambda item: item["trend_score"], reverse=True)

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
        "trend_count": len(labeled_summaries),
        "production_cluster_count": len(production_summaries),
        "videos": rows,
        "trend_summaries": labeled_summaries,
        "production_trend_summaries": production_summaries,
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
        f"{payload['trend_count']} labeled trends, "
        f"{payload['production_cluster_count']} production clusters"
    )


if __name__ == "__main__":
    main()
