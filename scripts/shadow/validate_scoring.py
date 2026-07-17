"""Validate shadow scoring against manager-labeled golden dataset."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

DATA_DIR = Path("data/shadow")
GOLDEN_JSON_PATH = DATA_DIR / "golden_dataset.json"
REPORT_PATH = DATA_DIR / "validation_report.md"

VALUE_RANK = {"high": 3, "normal": 2, "low": 1}


def precision_at_k(ranked: list[dict], k: int) -> float:
    if not ranked:
        return 0.0
    top = ranked[:k]
    hits = sum(1 for item in top if item.get("manager_value") == "high")
    return hits / min(k, len(top))


def run_validation(
    *,
    input_path: Path = GOLDEN_JSON_PATH,
    output_path: Path = REPORT_PATH,
    top_k: int = 15,
) -> bool:
    data = json.loads(input_path.read_text(encoding="utf-8"))
    trends = data.get("trend_summaries", [])
    videos = data.get("videos", [])

    ranked_by_score = sorted(trends, key=lambda t: t["trend_score"], reverse=True)
    ranked_by_manager = sorted(
        trends,
        key=lambda t: (VALUE_RANK.get(t.get("manager_value", "normal"), 0), t["trend_score"]),
        reverse=True,
    )

    high_value_in_top10 = [t for t in ranked_by_score[:10] if t.get("manager_value") == "high"]
    low_value_in_top10 = [t for t in ranked_by_score[:10] if t.get("manager_value") == "low"]

    breakout_top = sorted(videos, key=lambda v: v["breakout_ratio"], reverse=True)[:15]
    multi_channel_trends = [
        t for t in trends if t.get("channel_count", 0) >= 3 and t.get("breakout_ge_2_pct", 0) >= 0.5
    ]

    p_at_k = precision_at_k(ranked_by_score, top_k)
    recall_high = 0.0
    high_trends = [t for t in trends if t.get("manager_value") == "high"]
    if high_trends:
        top_ids = {t["trend_id"] for t in ranked_by_score[:top_k]}
        recall_high = sum(1 for t in high_trends if t["trend_id"] in top_ids) / len(high_trends)

    lines = [
        "# Shadow Validation Report",
        "",
        f"Generated: {datetime.now(UTC).isoformat()}",
        f"Source built at: {data.get('built_at', 'unknown')}",
        "",
        "## Dataset Summary",
        "",
        f"- Videos: {data.get('video_count', len(videos))}",
        f"- Channels: {data.get('channel_count', 0)}",
        f"- Labeled trends: {data.get('trend_count', len(trends))}",
        "",
        "## Scoring Validation Metrics",
        "",
        f"- Precision@{top_k} (high-value trends in top rank): **{p_at_k:.1%}**",
        f"- Recall of high-value trends in top {top_k}: **{recall_high:.1%}**",
        f"- Multi-channel breakout trends (≥3 channels, ≥50% breakout≥2): **{len(multi_channel_trends)}**",
        f"- High-value trends in algorithmic top 10: **{len(high_value_in_top10)}**",
        f"- Low-value counter-examples in algorithmic top 10: **{len(low_value_in_top10)}** (target: 0)",
        "",
        "## Acceptance Checks",
        "",
    ]

    checks = [
        (
            "Clear breakout trends rank above median",
            len(high_value_in_top10) >= 3,
        ),
        (
            "Low-value generic/manhwa trends not dominating top 10",
            len(low_value_in_top10) <= 1,
        ),
        (
            "At least one multi-channel resonance trend detected",
            len(multi_channel_trends) >= 1,
        ),
        (
            f"Precision@{top_k} ≥ 60%",
            p_at_k >= 0.6,
        ),
        (
            "BreakoutRatio is populated for all videos",
            all("breakout_ratio" in v for v in videos),
        ),
    ]

    for label, passed in checks:
        status = "PASS" if passed else "FAIL"
        lines.append(f"- [{status}] {label}")

    lines.extend(["", "## Top 15 Trends by Algorithm Score", ""])
    lines.append("| Rank | Trend | Score | Channels | Median Breakout | Manager Value |")
    lines.append("| ---: | --- | ---: | ---: | ---: | --- |")
    for idx, trend in enumerate(ranked_by_score[:15], start=1):
        lines.append(
            f"| {idx} | {trend['trend_name']} | {trend['trend_score']} | "
            f"{trend.get('channel_count', 0)} | {trend.get('median_breakout', 0)} | "
            f"{trend.get('manager_value', '')} |"
        )

    lines.extend(["", "## Top 15 Videos by BreakoutRatio", ""])
    lines.append("| Rank | Title | Channel | Views | Breakout | Label | Trend |")
    lines.append("| ---: | --- | --- | ---: | ---: | --- | --- |")
    for idx, video in enumerate(breakout_top, start=1):
        title = video["title"][:60].replace("|", "/")
        lines.append(
            f"| {idx} | {title} | {video['channel_name']} | {video['views']} | "
            f"{video['breakout_ratio']} | {video['breakout_label']} | {video['trend_name']} |"
        )

    lines.extend(["", "## Manager Value Ranking (reference)", ""])
    for idx, trend in enumerate(ranked_by_manager[:10], start=1):
        lines.append(
            f"{idx}. **{trend['trend_name']}** ({trend.get('manager_value')}) — "
            f"algo score {trend['trend_score']}"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "BreakoutRatio compares each video's views/hour against its channel's median for the same age bucket. "
            "Trend score weights cross-channel resonance (35%) and relative breakout (25%) so coordinated topics "
            "with abnormal per-channel performance rise to the top, while routine uploads from large channels stay muted.",
            "",
            "Known calibration gap: Hindi and manhwa crossover clusters can score high on resonance alone. "
            "Stage 2 should add language filters and manager-value penalties in the production scorer.",
            "",
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Validation report written to {output_path}")
    print(f"Precision@{top_k}: {p_at_k:.1%} | Recall high-value: {recall_high:.1%}")
    return all(passed for _, passed in checks)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate trend scoring on golden dataset")
    parser.add_argument("--input", type=Path, default=GOLDEN_JSON_PATH)
    parser.add_argument("--output", type=Path, default=REPORT_PATH)
    parser.add_argument("--top-k", type=int, default=15)
    args = parser.parse_args()
    if not run_validation(input_path=args.input, output_path=args.output, top_k=args.top_k):
        sys.exit(1)


if __name__ == "__main__":
    main()
