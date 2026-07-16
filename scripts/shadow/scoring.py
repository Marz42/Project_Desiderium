"""Shadow validation scoring: age buckets, velocity, baselines, BreakoutRatio."""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

AgeBucket = Literal["0_6h", "6_24h", "24_72h", "3_7d", "7d_plus"]

AGE_BUCKETS: list[tuple[AgeBucket, float, float]] = [
    ("0_6h", 0, 6),
    ("6_24h", 6, 24),
    ("24_72h", 24, 72),
    ("3_7d", 72, 168),
]

EPSILON = 1e-6
MIN_AGE_HOURS = 2.0
BASELINE_SAMPLE_SIZE = 20
CAPPED_BREAKOUT = 8.0

Tier = Literal["priority", "general", "experimental"]

TIER_WEIGHTS: dict[Tier, float] = {
    "priority": 1.5,
    "general": 1.0,
    "experimental": 0.5,
}


@dataclass(frozen=True)
class VideoRecord:
    video_id: str
    channel_id: str
    channel_name: str
    title: str
    published_at: datetime
    views: int
    likes: int | None
    comments: int | None
    duration_seconds: int
    tier: Tier = "priority"
    url: str = ""


def parse_iso_datetime(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value).astimezone(UTC)


def parse_duration_seconds(iso_duration: str) -> int:
    """Parse ISO 8601 duration like PT1H2M3S into seconds."""
    if not iso_duration.startswith("PT"):
        return 0
    duration = iso_duration[2:]
    hours = minutes = seconds = 0
    number = ""
    for char in duration:
        if char.isdigit():
            number += char
            continue
        if not number:
            continue
        if char == "H":
            hours = int(number)
        elif char == "M":
            minutes = int(number)
        elif char == "S":
            seconds = int(number)
        number = ""
    return hours * 3600 + minutes * 60 + seconds


def video_age_hours(published_at: datetime, now: datetime | None = None) -> float:
    now = now or datetime.now(UTC)
    return max((now - published_at).total_seconds() / 3600.0, 0.0)


def assign_age_bucket(age_hours: float) -> AgeBucket:
    for bucket, low, high in AGE_BUCKETS:
        if low <= age_hours < high:
            return bucket
    return "7d_plus"


def cold_start_velocity(views: int, age_hours: float) -> float:
    return views / max(age_hours, MIN_AGE_HOURS)


def compute_channel_baselines(
    videos: list[VideoRecord],
    *,
    now: datetime | None = None,
    sample_size: int = BASELINE_SAMPLE_SIZE,
) -> dict[tuple[str, AgeBucket], dict[str, float | int | str]]:
    """Median velocity per channel and age bucket from recent videos."""
    now = now or datetime.now(UTC)
    grouped: dict[tuple[str, AgeBucket], list[float]] = {}

    for video in videos:
        age = video_age_hours(video.published_at, now)
        bucket = assign_age_bucket(age)
        if bucket == "7d_plus":
            continue
        velocity = cold_start_velocity(video.views, age)
        grouped.setdefault((video.channel_id, bucket), []).append(velocity)

    baselines: dict[tuple[str, AgeBucket], dict[str, float | int | str]] = {}
    for key, velocities in grouped.items():
        channel_id, bucket = key
        sample = velocities[-sample_size:]
        count = len(sample)
        if count == 0:
            continue
        median = statistics.median(sample)
        confidence = (
            "high" if count >= 20 else "medium" if count >= 10 else "low" if count >= 5 else "very_low"
        )
        baselines[key] = {
            "channel_id": channel_id,
            "age_bucket": bucket,
            "median_velocity": median,
            "sample_count": count,
            "confidence": confidence,
        }
    return baselines


def global_baseline_by_bucket(
    videos: list[VideoRecord],
    *,
    now: datetime | None = None,
) -> dict[AgeBucket, float]:
    now = now or datetime.now(UTC)
    grouped: dict[AgeBucket, list[float]] = {}
    for video in videos:
        age = video_age_hours(video.published_at, now)
        bucket = assign_age_bucket(age)
        if bucket == "7d_plus":
            continue
        grouped.setdefault(bucket, []).append(cold_start_velocity(video.views, age))

    return {
        bucket: statistics.median(values) if values else 1.0
        for bucket, values in grouped.items()
    }


def breakout_ratio(
    video: VideoRecord,
    baselines: dict[tuple[str, AgeBucket], dict[str, float | int | str]],
    global_fallback: dict[AgeBucket, float],
    *,
    now: datetime | None = None,
) -> dict[str, float | str]:
    now = now or datetime.now(UTC)
    age = video_age_hours(video.published_at, now)
    bucket = assign_age_bucket(age)
    velocity = cold_start_velocity(video.views, age)

    baseline_entry = baselines.get((video.channel_id, bucket))
    if baseline_entry:
        baseline_velocity = float(baseline_entry["median_velocity"])
        confidence = str(baseline_entry["confidence"])
        source = "channel_median"
    else:
        baseline_velocity = global_fallback.get(bucket, 1.0)
        confidence = "low"
        source = "global_fallback"

    ratio = velocity / max(baseline_velocity, EPSILON)
    capped = min(ratio, CAPPED_BREAKOUT)

    if ratio < 0.75:
        label = "below_average"
    elif ratio < 1.5:
        label = "normal"
    elif ratio < 2.0:
        label = "above_average"
    elif ratio < 4.0:
        label = "breakout"
    else:
        label = "strong_breakout"

    return {
        "age_hours": round(age, 2),
        "age_bucket": bucket,
        "velocity": round(velocity, 2),
        "baseline_velocity": round(baseline_velocity, 2),
        "breakout_ratio": round(ratio, 3),
        "capped_breakout": round(capped, 3),
        "breakout_label": label,
        "baseline_confidence": confidence,
        "baseline_source": source,
    }


def score_trend_cluster(
    members: list[dict[str, Any]],
    *,
    now: datetime | None = None,
) -> dict[str, float | int | str | bool]:
    """Compute cross-channel resonance and composite trend score for a cluster."""
    now = now or datetime.now(UTC)
    if not members:
        return {"trend_score": 0.0}

    channels: dict[str, float] = {}
    breakout_values: list[float] = []
    breakout_ge_2 = 0
    total_views = 0
    recent_24h = 0
    recent_72h = 0

    for member in members:
        channel_id = member["channel_id"]
        tier = member.get("tier", "general")
        weight = TIER_WEIGHTS.get(tier, 1.0)
        channels[channel_id] = max(channels.get(channel_id, 0.0), weight)

        ratio = float(member.get("capped_breakout", member.get("breakout_ratio", 1.0)))
        breakout_values.append(ratio)
        if ratio >= 2.0:
            breakout_ge_2 += 1
        total_views += int(member.get("views", 0))

        published = member.get("published_at")
        if isinstance(published, str):
            published = parse_iso_datetime(published)
        age_h = video_age_hours(published, now) if published else 9999
        if age_h <= 24:
            recent_24h += 1
        if age_h <= 72:
            recent_72h += 1

    weighted_channel_count = sum(channels.values())
    target_channels = 8.0
    channel_resonance = 100 * min(
        math.log1p(weighted_channel_count) / math.log1p(target_channels),
        1.0,
    )

    median_breakout = statistics.median(breakout_values) if breakout_values else 1.0
    breakout_ratio_ge_2_pct = breakout_ge_2 / len(members)
    relative_breakout = min(100.0, 60 * median_breakout + 40 * breakout_ratio_ge_2_pct * 100)

    momentum = min(100.0, 25 * recent_24h + 10 * recent_72h)
    persistence = min(100.0, 15 * len(channels))
    absolute_scale = min(100.0, math.log1p(total_views) * 8)
    novelty = 100.0 if recent_24h >= 2 else 70.0 if recent_72h >= 3 else 40.0

    trend_score = (
        0.35 * channel_resonance
        + 0.25 * relative_breakout
        + 0.20 * momentum
        + 0.10 * persistence
        + 0.05 * absolute_scale
        + 0.05 * novelty
    )

    meets_standard = recent_72h >= 3 and breakout_ratio_ge_2_pct >= 0.5
    meets_early = recent_24h >= 2 and max(breakout_values, default=0) >= 4.0

    return {
        "trend_score": round(trend_score, 2),
        "channel_count": len(channels),
        "weighted_channel_count": round(weighted_channel_count, 2),
        "channel_resonance": round(channel_resonance, 2),
        "relative_breakout": round(relative_breakout, 2),
        "median_breakout": round(median_breakout, 3),
        "breakout_ge_2_pct": round(breakout_ratio_ge_2_pct, 3),
        "videos_24h": recent_24h,
        "videos_72h": recent_72h,
        "meets_standard_threshold": meets_standard,
        "meets_early_signal": meets_early,
    }
