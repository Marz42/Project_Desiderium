"""Generate read-only G4 funnel and historical-snapshot association reports."""

from __future__ import annotations

import argparse
import asyncio
import csv
import statistics
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import get_session_factory
from app.domain.trend_metrics import video_age_hours
from app.models import (
    BaselineConfidence,
    DailyCandidate,
    PublicationRecord,
    PublicationStatus,
)
from app.services.scoring_config import get_scoring_config

WINDOW_KEYS = ("initial", "24h", "72h", "7d")
CSV_FIELDS = [
    "group_type",
    "group",
    "window",
    "sample_count",
    "median_ratio",
    "mean_ratio",
    "above_one_share",
    "p25",
    "p75",
    "low_confidence_share",
    "late_backfill_share",
]


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * fraction
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _stats(snapshots: list[Any]) -> dict[str, Any]:
    ratios = [
        float(snapshot.observed_ratio_at_window or snapshot.performance_ratio)
        for snapshot in snapshots
        if (snapshot.observed_ratio_at_window or snapshot.performance_ratio) is not None
    ]
    return {
        "sample_count": len(ratios),
        "median_ratio": statistics.median(ratios) if ratios else None,
        "mean_ratio": statistics.mean(ratios) if ratios else None,
        "above_one_share": sum(value > 1.0 for value in ratios) / len(ratios) if ratios else None,
        "p25": _percentile(ratios, 0.25),
        "p75": _percentile(ratios, 0.75),
        "low_confidence_share": (
            sum(snapshot.baseline_confidence == BaselineConfidence.LOW for snapshot in snapshots)
            / len(snapshots)
            if snapshots
            else None
        ),
        "late_backfill_share": (
            sum(snapshot.late_backfill for snapshot in snapshots) / len(snapshots)
            if snapshots
            else None
        ),
    }


def _score_groups(records: list[PublicationRecord]) -> dict[str, str]:
    scored = sorted(
        (
            float(record.daily_candidate.trend_score_snapshot),
            str(record.id),
        )
        for record in records
        if record.daily_candidate
        and record.daily_candidate.trend_score_snapshot is not None
    )
    if not scored:
        return {}
    first_cut = scored[max(len(scored) // 3 - 1, 0)][0]
    second_cut = scored[max((2 * len(scored)) // 3 - 1, 0)][0]
    return {
        record_id: ("low" if score <= first_cut else "mid" if score <= second_cut else "high")
        for score, record_id in scored
    }


async def build() -> tuple[str, list[dict[str, Any]]]:
    config = get_scoring_config()
    now = datetime.now(UTC)
    session_factory = get_session_factory()
    async with session_factory() as session:
        candidates = list((await session.scalars(select(DailyCandidate))).all())
        records = list(
            (
                await session.scalars(
                    select(PublicationRecord).options(
                        selectinload(PublicationRecord.metric_snapshots),
                        selectinload(PublicationRecord.daily_candidate),
                    ),
                )
            ).all(),
        )

    selected = [candidate for candidate in candidates if candidate.selected]
    adopted = [record for record in records if record.status == PublicationStatus.ADOPTED]
    published = [record for record in records if record.status == PublicationStatus.PUBLISHED]

    mature_denominators = dict.fromkeys(WINDOW_KEYS, 0)
    observed_counts = dict.fromkeys(WINDOW_KEYS, 0)
    grouped: dict[tuple[str, str, str], list[Any]] = defaultdict(list)
    score_groups = _score_groups(published)
    for record in published:
        if record.published_at is None:
            continue
        age = video_age_hours(record.published_at, now)
        snapshots = {snapshot.window_key.value: snapshot for snapshot in record.metric_snapshots}
        lifecycle = (
            record.daily_candidate.lifecycle_status_snapshot.value
            if record.daily_candidate and record.daily_candidate.lifecycle_status_snapshot
            else "unknown"
        )
        score_group = score_groups.get(str(record.id), "unknown")
        for key, target_hours in zip(WINDOW_KEYS, config.publication.windows_hours):
            if age < target_hours:
                continue
            mature_denominators[key] += 1
            snapshot = snapshots.get(key)
            if snapshot is None:
                continue
            observed_counts[key] += 1
            grouped[("lifecycle", lifecycle, key)].append(snapshot)
            grouped[("trend_score_tertile", score_group, key)].append(snapshot)

    rows: list[dict[str, Any]] = []
    for (group_type, group, window), grouped_snapshots in sorted(grouped.items()):
        rows.append(
            {
                "group_type": group_type,
                "group": group,
                "window": window,
                **_stats(grouped_snapshots),
            },
        )

    lines = [
        "# G4 Beta Observation",
        "",
        "Association only; this report does not estimate causal lift.",
        "",
        f"- Candidates: {len(candidates)}",
        f"- Selected: {len(selected)} ({len(selected) / len(candidates):.1%})"
        if candidates
        else "- Selected: 0",
        f"- Adopted records: {len(adopted)}",
        f"- Published records: {len(published)}",
        "",
        "## Mature-window recovery",
    ]
    for key in WINDOW_KEYS:
        denominator = mature_denominators[key]
        observed = observed_counts[key]
        ratio = observed / denominator if denominator else 0.0
        lines.append(f"- {key}: {observed}/{denominator} ({ratio:.1%})")
    lines.extend(
        [
            "",
            "Right-censored records that have not reached a window are excluded from its denominator.",
        ],
    )
    return "\n".join(lines) + "\n", rows


async def _main(output_dir: Path) -> None:
    markdown, rows = await build()
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "g4-report.md").write_text(markdown, encoding="utf-8")
    with (output_dir / "g4-groups.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/observation"),
    )
    args = parser.parse_args()
    asyncio.run(_main(args.output_dir))
