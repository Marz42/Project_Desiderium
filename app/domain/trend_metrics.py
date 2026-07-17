"""Pure trend metric calculations (no DB, no LLM).

Migrated from scripts/shadow/scoring.py into the application domain layer.
"""

from __future__ import annotations

import math
import statistics
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from app.models import AgeBucket, BaselineConfidence
from app.services.scoring_config import ScoringConfig, get_scoring_config

AgeBucketKey = Literal["0_6h", "6_24h", "24_72h", "3_7d", "7d_plus"]

AGE_BUCKETS: list[tuple[AgeBucketKey, float, float]] = [
    ("0_6h", 0, 6),
    ("6_24h", 6, 24),
    ("24_72h", 24, 72),
    ("3_7d", 72, 168),
]

Tier = Literal["priority", "general", "experimental"]


@dataclass(frozen=True)
class VideoMetricsInput:
    content_item_id: str
    channel_external_id: str
    channel_name: str
    title: str
    published_at: datetime
    views: int
    likes: int | None
    comments: int | None
    duration_seconds: int
    tier: Tier = "general"
    url: str = ""


def _channel_id(video: VideoMetricsInput) -> str:
    return video.channel_external_id


def parse_iso_datetime(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value).astimezone(UTC)


def normalize_title(title: str) -> str:
    lowered = unicodedata.normalize("NFKC", title).lower()
    return " ".join(lowered.split())


def video_age_hours(published_at: datetime, now: datetime | None = None) -> float:
    now = now or datetime.now(UTC)
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    return max(
        (now.astimezone(UTC) - published_at.astimezone(UTC)).total_seconds() / 3600.0,
        0.0,
    )


def assign_age_bucket(age_hours: float) -> AgeBucketKey:
    for bucket, low, high in AGE_BUCKETS:
        if low <= age_hours < high:
            return bucket
    return "7d_plus"


def age_bucket_key_to_model(bucket: AgeBucketKey) -> AgeBucket | None:
    mapping: dict[AgeBucketKey, AgeBucket] = {
        "0_6h": AgeBucket.H0_6,
        "6_24h": AgeBucket.H6_24,
        "24_72h": AgeBucket.H24_72,
        "3_7d": AgeBucket.D3_7,
    }
    return mapping.get(bucket)


def age_bucket_model_to_key(bucket: AgeBucket) -> AgeBucketKey:
    mapping: dict[AgeBucket, AgeBucketKey] = {
        AgeBucket.H0_6: "0_6h",
        AgeBucket.H6_24: "6_24h",
        AgeBucket.H24_72: "24_72h",
        AgeBucket.D3_7: "3_7d",
    }
    return mapping[bucket]


def cold_start_velocity(
    views: int, age_hours: float, *, config: ScoringConfig | None = None
) -> float:
    cfg = config or get_scoring_config()
    return views / max(age_hours, cfg.min_age_hours)


def snapshot_velocity(
    new_views: int,
    old_views: int,
    hours_between: float,
    *,
    config: ScoringConfig | None = None,
) -> float:
    cfg = config or get_scoring_config()
    if hours_between <= 0:
        return 0.0
    return max(new_views - old_views, 0) / max(hours_between, cfg.min_age_hours)


def hour_bucket(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).replace(minute=0, second=0, microsecond=0)


def snapshot_interval_hours(
    age_hours: float, *, config: ScoringConfig | None = None
) -> float | None:
    """Return required hours between snapshots for a video age, or None if inactive."""
    cfg = config or get_scoring_config()
    if age_hours < 24:
        return cfg.snapshots.age_0_24h_interval_hours
    if age_hours < 72:
        return cfg.snapshots.age_1_3d_interval_hours
    if age_hours < 168:
        return cfg.snapshots.age_3_7d_interval_hours
    return None


def is_snapshot_due(
    last_captured_at: datetime | None,
    published_at: datetime | None,
    now: datetime | None = None,
    *,
    config: ScoringConfig | None = None,
) -> bool:
    if published_at is None:
        return False
    now = now or datetime.now(UTC)
    age = video_age_hours(published_at, now)
    interval = snapshot_interval_hours(age, config=config)
    if interval is None:
        return False
    if last_captured_at is None:
        return True
    hours_since = (now - last_captured_at).total_seconds() / 3600.0
    return hours_since >= interval


def baseline_confidence_label(
    sample_count: int,
    *,
    config: ScoringConfig | None = None,
) -> tuple[str, BaselineConfidence]:
    cfg = config or get_scoring_config()
    if sample_count >= cfg.baselines.confidence_high_min:
        return "high", BaselineConfidence.HIGH
    if sample_count >= cfg.baselines.confidence_medium_min:
        return "medium", BaselineConfidence.MEDIUM
    if sample_count >= cfg.baselines.confidence_low_min:
        return "low", BaselineConfidence.LOW
    return "very_low", BaselineConfidence.LOW


def tier_weight(tier: Tier | str, *, config: ScoringConfig | None = None) -> float:
    cfg = config or get_scoring_config()
    mapping = {
        "priority": cfg.channels.priority,
        "general": cfg.channels.general,
        "experimental": cfg.channels.experimental,
    }
    return mapping.get(str(tier), cfg.channels.general)


def compute_channel_baselines(
    videos: list[VideoMetricsInput],
    *,
    now: datetime | None = None,
    config: ScoringConfig | None = None,
) -> dict[tuple[str, AgeBucketKey], dict[str, float | int | str]]:
    cfg = config or get_scoring_config()
    now = now or datetime.now(UTC)
    grouped: dict[tuple[str, AgeBucketKey], list[float]] = {}

    for video in videos:
        age = video_age_hours(video.published_at, now)
        bucket = assign_age_bucket(age)
        if bucket == "7d_plus":
            continue
        velocity = cold_start_velocity(video.views, age, config=cfg)
        grouped.setdefault((_channel_id(video), bucket), []).append(velocity)

    baselines: dict[tuple[str, AgeBucketKey], dict[str, float | int | str]] = {}
    for key, velocities in grouped.items():
        channel_id, bucket = key
        sample = velocities[-cfg.baselines.sample_size :]
        count = len(sample)
        if count == 0:
            continue
        median = statistics.median(sample)
        label, _ = baseline_confidence_label(count, config=cfg)
        baselines[key] = {
            "channel_id": channel_id,
            "age_bucket": bucket,
            "median_velocity": median,
            "sample_count": count,
            "confidence": label,
        }
    return baselines


def global_baseline_by_bucket(
    videos: list[VideoMetricsInput],
    *,
    now: datetime | None = None,
) -> dict[AgeBucketKey, float]:
    now = now or datetime.now(UTC)
    grouped: dict[AgeBucketKey, list[float]] = {}
    for video in videos:
        age = video_age_hours(video.published_at, now)
        bucket = assign_age_bucket(age)
        if bucket == "7d_plus":
            continue
        grouped.setdefault(bucket, []).append(
            cold_start_velocity(video.views, age),
        )

    return {
        bucket: statistics.median(values) if values else 1.0 for bucket, values in grouped.items()
    }


def breakout_ratio(
    video: VideoMetricsInput,
    baselines: dict[tuple[str, AgeBucketKey], dict[str, float | int | str]],
    global_fallback: dict[AgeBucketKey, float],
    *,
    now: datetime | None = None,
    config: ScoringConfig | None = None,
) -> dict[str, float | str]:
    cfg = config or get_scoring_config()
    now = now or datetime.now(UTC)
    age = video_age_hours(video.published_at, now)
    bucket = assign_age_bucket(age)
    velocity = cold_start_velocity(video.views, age, config=cfg)

    baseline_entry = baselines.get((_channel_id(video), bucket))
    if baseline_entry:
        baseline_velocity = float(baseline_entry["median_velocity"])
        confidence = str(baseline_entry["confidence"])
        source = "channel_median"
    else:
        baseline_velocity = global_fallback.get(bucket, 1.0)
        confidence = "low"
        source = "global_fallback"

    ratio = velocity / max(baseline_velocity, cfg.epsilon)
    capped = min(ratio, cfg.capped_breakout_max)

    if ratio < cfg.thresholds.below_average:
        label = "below_average"
    elif ratio < cfg.thresholds.normal:
        label = "normal"
    elif ratio < cfg.thresholds.above_average:
        label = "above_average"
    elif ratio < cfg.thresholds.strong_breakout:
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
    config: ScoringConfig | None = None,
) -> dict[str, float | int | str | bool]:
    """Compute cross-channel resonance and composite trend score for a cluster."""
    cfg = config or get_scoring_config()
    now = now or datetime.now(UTC)
    if not members:
        return {"trend_score": 0.0}

    channels: dict[str, float] = {}
    breakout_values: list[float] = []
    breakout_ge_2 = 0
    total_views = 0
    recent_24h = 0
    recent_72h = 0
    channels_24h: set[str] = set()
    channels_72h: set[str] = set()
    has_priority_or_keyword_evidence = False

    for member in members:
        channel_id = str(member["channel_id"])
        tier = member.get("tier", "general")
        weight = tier_weight(tier, config=cfg)
        channels[channel_id] = max(channels.get(channel_id, 0.0), weight)
        if tier in {"priority", "experimental"} or member.get("source_kind") in {
            "keyword",
            "ranking",
        }:
            has_priority_or_keyword_evidence = True

        ratio = float(member.get("capped_breakout", member.get("breakout_ratio", 1.0)))
        breakout_values.append(ratio)
        if ratio >= cfg.thresholds.breakout:
            breakout_ge_2 += 1
        total_views += int(member.get("views", 0))

        published = member.get("published_at")
        if isinstance(published, str):
            published = parse_iso_datetime(published)
        age_h = video_age_hours(published, now) if published else 9999
        if age_h <= 24:
            recent_24h += 1
            channels_24h.add(channel_id)
        if age_h <= 72:
            recent_72h += 1
            channels_72h.add(channel_id)

    weighted_channel_count = sum(channels.values())
    channel_resonance = 100 * min(
        math.log1p(weighted_channel_count) / math.log1p(cfg.target_channel_count),
        1.0,
    )

    median_breakout = statistics.median(breakout_values) if breakout_values else 1.0
    breakout_ratio_ge_2_pct = breakout_ge_2 / len(members)
    relative_breakout = min(
        100.0,
        cfg.relative_breakout.median_weight * median_breakout * 100
        + cfg.relative_breakout.pct_ge_2_weight
        * breakout_ratio_ge_2_pct
        * cfg.relative_breakout.pct_ge_2_scale,
    )

    momentum = min(
        100.0,
        cfg.momentum.recent_24h_multiplier * recent_24h
        + cfg.momentum.recent_72h_multiplier * recent_72h,
    )
    persistence = min(
        100.0,
        cfg.momentum.persistence_channel_multiplier * len(channels),
    )
    absolute_scale = min(
        100.0,
        math.log1p(total_views) * cfg.momentum.absolute_scale_log_multiplier,
    )

    if recent_24h >= cfg.novelty.fresh_24h_min_videos:
        novelty = cfg.novelty.fresh_24h_score
    elif recent_72h >= cfg.novelty.fresh_72h_min_videos:
        novelty = cfg.novelty.fresh_72h_score
    else:
        novelty = cfg.novelty.fresh_7d_score

    trend_score = (
        cfg.weights.channel_resonance * channel_resonance
        + cfg.weights.relative_breakout * relative_breakout
        + cfg.weights.momentum * momentum
        + cfg.weights.persistence * persistence
        + cfg.weights.absolute_scale * absolute_scale
        + cfg.weights.novelty * novelty
    )

    meets_standard = (
        len(channels_72h) >= cfg.thresholds.standard_min_channels_72h
        and breakout_ratio_ge_2_pct >= cfg.thresholds.standard_breakout_ge_2_pct
    )
    meets_early = (
        len(channels_24h) >= cfg.thresholds.early_min_channels_24h
        and recent_24h >= cfg.thresholds.early_min_videos_24h
        and max(breakout_values, default=0) >= cfg.thresholds.strong_breakout
        and (has_priority_or_keyword_evidence or len(channels_24h) >= 3)
    )

    return {
        "trend_score": round(trend_score, 2),
        "channel_count": len(channels),
        "channels_24h": len(channels_24h),
        "channels_72h": len(channels_72h),
        "weighted_channel_count": round(weighted_channel_count, 2),
        "channel_resonance": round(channel_resonance, 2),
        "relative_breakout": round(relative_breakout, 2),
        "median_breakout": round(median_breakout, 3),
        "breakout_ge_2_pct": round(breakout_ratio_ge_2_pct, 3),
        "momentum": round(momentum, 2),
        "persistence": round(persistence, 2),
        "absolute_scale": round(absolute_scale, 2),
        "novelty": round(novelty, 2),
        "videos_24h": recent_24h,
        "videos_72h": recent_72h,
        "meets_standard_threshold": meets_standard,
        "meets_early_signal": meets_early,
    }


def compute_growth_ratio(
    activity_last_24h: float,
    activity_previous_24h: float,
    *,
    config: ScoringConfig | None = None,
) -> float:
    cfg = config or get_scoring_config()
    return activity_last_24h / max(activity_previous_24h, cfg.epsilon)


def cluster_activity(
    members: list[dict[str, Any]],
    *,
    now: datetime | None = None,
    config: ScoringConfig | None = None,
) -> float:
    """Weighted activity for videos published in the last 24 hours."""
    cfg = config or get_scoring_config()
    now = now or datetime.now(UTC)
    total = 0.0
    for member in members:
        published = member.get("published_at")
        if isinstance(published, str):
            published = parse_iso_datetime(published)
        if published is None:
            continue
        if video_age_hours(published, now) > 24:
            continue
        tier = member.get("tier", "general")
        weight = tier_weight(tier, config=cfg)
        capped = float(member.get("capped_breakout", 1.0))
        incremental = float(member.get("incremental_views", member.get("views", 0)))
        normalized_increment = math.log1p(max(incremental, 0))
        total += weight * capped * normalized_increment
    return total
