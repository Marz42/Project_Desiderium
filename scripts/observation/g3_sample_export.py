"""Export G3 decisions for human labeling without leaking holdout labels."""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.db import get_session_factory
from app.models import ClusterDecisionAudit

FIELDS = [
    "analysis_run_id",
    "decision_audit_id",
    "decision_source",
    "retriever_mode",
    "degraded",
    "embedding_space_id",
    "source_item",
    "selected_trend",
    "top_k_candidate_trends",
    "similarity_scores",
    "entity_constraints",
    "thresholds",
    "llm_result",
    "final_action",
    "human_label",
    "dataset_split",
]


def _split(audit_id: str) -> str:
    bucket = int(hashlib.sha256(audit_id.encode("ascii")).hexdigest()[:8], 16) % 5
    return "holdout_regression_set" if bucket == 0 else "calibration_set"


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True) if value is not None else ""


def _row(audit: ClusterDecisionAudit) -> dict[str, str]:
    evidence = audit.evidence or {}
    audit_id = str(audit.id)
    return {
        "analysis_run_id": str(evidence.get("analysis_run_id") or ""),
        "decision_audit_id": audit_id,
        "decision_source": audit.source.value,
        "retriever_mode": str(evidence.get("retriever_mode") or ""),
        "degraded": str(bool(evidence.get("degraded"))).lower(),
        "embedding_space_id": audit.embedding_space or "",
        "source_item": _json(evidence.get("source_item")),
        "selected_trend": str(audit.target_trend_id or ""),
        "top_k_candidate_trends": _json(evidence.get("top_k_candidate_trends")),
        "similarity_scores": _json(evidence.get("similarity_scores")),
        "entity_constraints": _json(evidence.get("entity_constraints")),
        "thresholds": _json(evidence.get("thresholds")),
        "llm_result": _json(evidence.get("llm_result")),
        "final_action": audit.action.value,
        "human_label": "",
        "dataset_split": _split(audit_id),
    }


def _write(path: Path, rows: list[dict[str, str]], *, frozen: bool) -> None:
    existing_ids: set[str] = set()
    mode = "w"
    write_header = True
    if frozen and path.exists():
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            existing_ids = {
                row["decision_audit_id"] for row in csv.DictReader(handle) if row.get("decision_audit_id")
            }
        mode = "a"
        write_header = path.stat().st_size == 0
    with path.open(mode, encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerows(row for row in rows if row["decision_audit_id"] not in existing_ids)


async def export(output_dir: Path) -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        audits = list(
            (
                await session.scalars(
                    select(ClusterDecisionAudit).order_by(ClusterDecisionAudit.created_at),
                )
            ).all(),
        )
    rows = [_row(audit) for audit in audits]
    output_dir.mkdir(parents=True, exist_ok=True)
    calibration = [row for row in rows if row["dataset_split"] == "calibration_set"]
    holdout = [row for row in rows if row["dataset_split"] == "holdout_regression_set"]
    _write(output_dir / "g3-calibration.csv", calibration, frozen=False)
    # Existing holdout rows and labels are never rewritten by later exports.
    _write(output_dir / "g3-holdout-regression.csv", holdout, frozen=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/observation"),
    )
    args = parser.parse_args()
    asyncio.run(export(args.output_dir))
