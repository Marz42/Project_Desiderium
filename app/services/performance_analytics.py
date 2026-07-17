"""G4 admin analytics: adoption/publish funnel + PerformanceRatio breakdowns.

IMPORTANT: every figure here describes an *association* between trend-engine
picks and public YouTube outcomes. It is NOT a causal measurement of "lift"
from any recommendation -- confounders (topic timing, thumbnail/title
quality, platform distribution algorithm) are not controlled for. The G4
observation gate additionally requires >=14 days and >=20 published records
before any conclusion is treated as reliable.
"""

from __future__ import annotations

import statistics
import uuid
from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AngleStatus, AngleStatusAudit, PublicationRecord
from app.repositories.publication_records import PublicationRecordRepository

SCORE_BANDS: list[tuple[float, float, str]] = [
    (0, 20, "0-20"),
    (20, 40, "20-40"),
    (40, 60, "40-60"),
    (60, 80, "60-80"),
    (80, float("inf"), "80+"),
]

WINDOW_ORDER = ("initial", "24h", "72h", "7d")


def _score_band(score: float | None) -> str:
    if score is None:
        return "unknown"
    for low, high, label in SCORE_BANDS:
        if low <= score < high:
            return label
    return "unknown"


def _avg_ratio_by_window(records: list[PublicationRecord]) -> dict[str, dict[str, Any]]:
    buckets: dict[str, list[float]] = defaultdict(list)
    for record in records:
        for snap in record.metric_snapshots:
            if snap.performance_ratio is not None:
                buckets[snap.window_key.value].append(snap.performance_ratio)
    return {
        key: {
            "count": len(buckets.get(key, [])),
            "avg_performance_ratio": (statistics.mean(buckets[key]) if buckets.get(key) else None),
        }
        for key in WINDOW_ORDER
    }


def _group_by_window(
    records: list[PublicationRecord],
    *,
    key: Any,
) -> dict[str, dict[str, dict[str, Any]]]:
    groups: dict[str, list[PublicationRecord]] = defaultdict(list)
    for record in records:
        groups[key(record)].append(record)
    return {group_key: _avg_ratio_by_window(group) for group_key, group in groups.items()}


class PerformanceAnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._records = PublicationRecordRepository(session)

    async def get_overview(self) -> dict[str, Any]:
        audits = await self._all_audits()
        funnel = self._compute_funnel(audits)
        records = await self._records.list_published_with_snapshots()

        return {
            "funnel": funnel,
            "window_stats": _avg_ratio_by_window(records),
            "by_format": _group_by_window(
                records,
                key=lambda r: r.format.value if r.format else "unknown",
            ),
            "by_lifecycle": _group_by_window(
                records,
                key=lambda r: (
                    r.daily_candidate.lifecycle_status_snapshot.value
                    if r.daily_candidate and r.daily_candidate.lifecycle_status_snapshot
                    else "unknown"
                ),
            ),
            "by_score_band": _group_by_window(
                records,
                key=lambda r: _score_band(
                    r.daily_candidate.trend_score_snapshot
                    if r.daily_candidate and r.daily_candidate.trend_score_snapshot is not None
                    else (
                        r.daily_candidate.candidate_score if r.daily_candidate else None
                    )
                ),
            ),
            "sample_size": len(records),
            "window_order": WINDOW_ORDER,
        }

    async def _all_audits(self) -> list[AngleStatusAudit]:
        stmt = select(AngleStatusAudit).order_by(AngleStatusAudit.created_at)
        return list((await self._session.scalars(stmt)).all())

    def _compute_funnel(self, audits: list[AngleStatusAudit]) -> dict[str, Any]:
        selected_ids: set[uuid.UUID] = set()
        adopted_first: dict[uuid.UUID, Any] = {}
        published_first: dict[uuid.UUID, Any] = {}

        for audit in audits:
            if audit.to_status == AngleStatus.SELECTED:
                selected_ids.add(audit.creative_angle_id)
            if audit.to_status == AngleStatus.ADOPTED:
                adopted_first.setdefault(audit.creative_angle_id, audit.created_at)
            if audit.to_status == AngleStatus.PUBLISHED:
                published_first.setdefault(audit.creative_angle_id, audit.created_at)

        adopted_ids = set(adopted_first)
        published_ids = set(published_first)

        adopt_rate = len(adopted_ids) / len(selected_ids) if selected_ids else None
        publish_rate = len(published_ids) / len(adopted_ids) if adopted_ids else None

        deltas_hours = [
            (published_first[angle_id] - adopted_first[angle_id]).total_seconds() / 3600.0
            for angle_id in published_ids & adopted_ids
            if published_first[angle_id] >= adopted_first[angle_id]
        ]
        avg_ttp = statistics.mean(deltas_hours) if deltas_hours else None

        return {
            "selected_count": len(selected_ids),
            "adopted_count": len(adopted_ids),
            "published_count": len(published_ids),
            "adopt_rate": adopt_rate,
            "publish_rate": publish_rate,
            "avg_time_to_publish_hours": avg_ttp,
        }
