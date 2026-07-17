"""Hard constraints for bounded trend merge decisions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any


@dataclass(frozen=True)
class ConstraintResult:
    allowed: bool
    reasons: tuple[str, ...]


def _as_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        from app.domain.trend_metrics import parse_iso_datetime

        return parse_iso_datetime(value)
    return None


def publish_gap_ok(
    left_published: Any,
    right_published: Any,
    *,
    max_gap_days: int,
) -> bool:
    left = _as_dt(left_published)
    right = _as_dt(right_published)
    if left is None or right is None:
        return True
    return abs(left - right) <= timedelta(days=max_gap_days)


def hard_constraints_allow_merge(
    source: dict[str, Any],
    candidate_trend: dict[str, Any],
    *,
    max_gap_days: int = 7,
) -> ConstraintResult:
    reasons: list[str] = []

    source_anime = (source.get("anime_title") or "").strip().lower()
    candidate_anime = (candidate_trend.get("anime_title") or "").strip().lower()
    if source_anime and candidate_anime and source_anime != candidate_anime:
        reasons.append("anime_title_conflict")

    source_entity = (source.get("entity_id") or "").strip()
    candidate_entity = (candidate_trend.get("entity_id") or "").strip()
    # Different concrete entity ids under same anime may still conflict on topic type.
    source_topic = (source.get("topic_type") or "").strip().lower()
    candidate_topic = (candidate_trend.get("topic_type") or "").strip().lower()
    if (
        source_entity
        and candidate_entity
        and source_entity != candidate_entity
        and source_topic in {"character", "arc", "event"}
        and candidate_topic in {"character", "arc", "event"}
        and source_topic == candidate_topic
    ):
        reasons.append("entity_conflict")

    source_lang = (source.get("language") or "").lower()
    candidate_lang = (candidate_trend.get("language") or "").lower()
    if source_lang and candidate_lang and source_lang[:2] != candidate_lang[:2]:
        reasons.append("language_conflict")

    if not publish_gap_ok(
        source.get("published_at"),
        candidate_trend.get("published_at"),
        max_gap_days=max_gap_days,
    ):
        reasons.append("publish_gap_exceeded")

    if candidate_trend.get("has_brief_or_publication"):
        reasons.append("protected_historical_trend")

    return ConstraintResult(allowed=not reasons, reasons=tuple(reasons))


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    return max(min(dot, 1.0), -1.0)
