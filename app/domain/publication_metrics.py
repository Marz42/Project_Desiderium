"""Pure calculations for G4 publication performance feedback (no DB, no HTTP)."""

from __future__ import annotations

import statistics

from app.models import CreativeFormat, PublicationWindowKey

WINDOW_ORDER: tuple[PublicationWindowKey, ...] = (
    PublicationWindowKey.INITIAL,
    PublicationWindowKey.H24,
    PublicationWindowKey.H72,
    PublicationWindowKey.D7,
)

# YouTube treats videos up to 3 minutes as Shorts-eligible; used only as a
# heuristic to label our own published videos short/long for baseline grouping.
SHORT_MAX_DURATION_SECONDS = 180


def classify_format(duration_seconds: int | None) -> CreativeFormat:
    """Best-effort short/long classification from video duration."""
    if duration_seconds is not None and duration_seconds <= SHORT_MAX_DURATION_SECONDS:
        return CreativeFormat.SHORT
    return CreativeFormat.LONG


def is_window_due(anchor_age_hours: float, target_hours: float) -> bool:
    """A window is due once the video is at least as old as its target hour mark."""
    return anchor_age_hours >= target_hours


def is_late_backfill(anchor_age_hours: float, target_hours: float, grace_hours: float) -> bool:
    """True if we captured a window well after its target time (missed schedule)."""
    return anchor_age_hours > target_hours + grace_hours


def median_velocity(samples: list[tuple[float, float]], min_age_hours: float) -> float | None:
    """Median views-per-hour velocity from (views, video_age_hours) samples."""
    if not samples:
        return None
    velocities = [views / max(age, min_age_hours) for views, age in samples]
    return statistics.median(velocities)


def compute_performance_ratio(velocity: float, baseline_velocity: float, epsilon: float) -> float:
    """Association-only ratio of observed velocity to the team baseline velocity."""
    return round(velocity / max(baseline_velocity, epsilon), 3)
