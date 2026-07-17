"""Generate a read-only G3 proxy-metrics report."""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.db import get_session_factory
from app.models import ClusterDecisionAudit, DailyCandidate, TrendTheme


async def build_report() -> str:
    session_factory = get_session_factory()
    async with session_factory() as session:
        audits = list(
            (
                await session.scalars(
                    select(ClusterDecisionAudit).order_by(ClusterDecisionAudit.created_at),
                )
            ).all(),
        )
        top_candidates = list(
            (
                await session.scalars(
                    select(DailyCandidate)
                    .where(DailyCandidate.rank <= 30)
                    .options(selectinload(DailyCandidate.trend))
                    .order_by(DailyCandidate.date, DailyCandidate.rank),
                )
            ).all(),
        )
        entity_counts = list(
            (
                await session.execute(
                    select(
                        TrendTheme.entities["entity_id"].astext,
                        func.count(TrendTheme.id),
                    )
                    .where(TrendTheme.active.is_(True))
                    .group_by(TrendTheme.entities["entity_id"].astext),
                )
            ).all(),
        )

    action_counts = Counter(audit.action.value for audit in audits)
    source_counts = Counter(audit.source.value for audit in audits)
    degraded_count = sum(bool((audit.evidence or {}).get("degraded")) for audit in audits)
    manual_merge_count = action_counts.get("manual_merge", 0)
    manual_move_out_count = action_counts.get("manual_move_out", 0)
    duplicated_entities = sum(1 for entity_id, count in entity_counts if entity_id and count > 1)

    duplicate_slots = 0
    seen_by_date: dict[object, set[tuple[str | None, str | None]]] = {}
    for candidate in top_candidates:
        trend = candidate.trend
        if trend is None:
            continue
        key = (trend.anime_title, (trend.entities or {}).get("facet"))
        seen = seen_by_date.setdefault(candidate.date, set())
        if key in seen:
            duplicate_slots += 1
        seen.add(key)
    duplicate_ratio = duplicate_slots / len(top_candidates) if top_candidates else 0.0

    lines = [
        "# G3 Beta Observation",
        "",
        "These are proxy metrics, not human-labeled merge/split error rates.",
        "",
        f"- Decisions: {len(audits)}",
        f"- Top-30 duplicate anime/facet slots: {duplicate_slots}/{len(top_candidates)} "
        f"({duplicate_ratio:.1%})",
        f"- Active entity combinations represented by multiple themes: {duplicated_entities}",
        f"- Manual merges: {manual_merge_count}",
        f"- Manual move-outs: {manual_move_out_count}",
        f"- Degraded retriever decisions: {degraded_count}",
        "",
        "## Actions",
        *[f"- {key}: {value}" for key, value in sorted(action_counts.items())],
        "",
        "## Sources",
        *[f"- {key}: {value}" for key, value in sorted(source_counts.items())],
    ]
    return "\n".join(lines) + "\n"


async def _main(output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(await build_report(), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("artifacts/observation/g3-report.md"))
    args = parser.parse_args()
    asyncio.run(_main(args.output))
