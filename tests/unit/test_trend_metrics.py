"""Unit tests for trend metrics domain layer."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.domain.trend_metrics import (
    assign_age_bucket,
    breakout_ratio,
    cold_start_velocity,
    compute_channel_baselines,
    global_baseline_by_bucket,
    is_snapshot_due,
    score_trend_cluster,
    snapshot_interval_hours,
    VideoMetricsInput,
)
from app.services.scoring_config import load_scoring_config


def _video(
    video_id: str,
    channel_id: str,
    views: int,
    hours_ago: float,
    *,
    tier: str = "priority",
    title: str = "test",
) -> VideoMetricsInput:
    return VideoMetricsInput(
        content_item_id=video_id,
        channel_external_id=channel_id,
        channel_name=f"Channel {channel_id}",
        title=title,
        published_at=datetime.now(UTC) - timedelta(hours=hours_ago),
        views=views,
        likes=None,
        comments=None,
        duration_seconds=600,
        tier=tier,  # type: ignore[arg-type]
    )


def test_age_buckets() -> None:
    assert assign_age_bucket(3) == "0_6h"
    assert assign_age_bucket(12) == "6_24h"
    assert assign_age_bucket(48) == "24_72h"
    assert assign_age_bucket(100) == "3_7d"
    assert assign_age_bucket(200) == "7d_plus"


def test_cold_start_velocity_uses_minimum_age() -> None:
    cfg = load_scoring_config()
    assert cold_start_velocity(1000, 0.5, config=cfg) == 500.0


def test_breakout_ratio_uses_channel_median() -> None:
    now = datetime.now(UTC)
    videos = [
        _video("a", "ch1", 1000, 12),
        _video("b", "ch1", 2000, 12),
        _video("c", "ch1", 3000, 12),
        _video("hot", "ch1", 50000, 12, title="breakout"),
    ]
    baselines = compute_channel_baselines(videos, now=now)
    fallback = global_baseline_by_bucket(videos, now=now)
    hot = next(v for v in videos if v.content_item_id == "hot")
    result = breakout_ratio(hot, baselines, fallback, now=now)
    assert result["breakout_ratio"] > 2.0
    assert result["baseline_source"] == "channel_median"


def test_capped_breakout_respects_config() -> None:
    cfg = load_scoring_config()
    now = datetime.now(UTC)
    videos = [_video("solo", "ch1", 1_000_000, 12)]
    baselines = compute_channel_baselines(videos, now=now)
    fallback = global_baseline_by_bucket(videos, now=now)
    result = breakout_ratio(videos[0], baselines, fallback, now=now)
    assert result["capped_breakout"] <= cfg.capped_breakout_max


def test_trend_score_favors_cross_channel_resonance() -> None:
    now = datetime.now(UTC)
    members = [
        {
            "channel_id": f"ch{i}",
            "tier": "priority",
            "capped_breakout": 3.0,
            "breakout_ratio": 3.0,
            "views": 50000,
            "published_at": (now - timedelta(hours=10)).isoformat(),
        }
        for i in range(4)
    ]
    single = [
        {
            "channel_id": "solo",
            "tier": "priority",
            "capped_breakout": 6.0,
            "breakout_ratio": 6.0,
            "views": 500000,
            "published_at": (now - timedelta(hours=10)).isoformat(),
        }
    ]
    multi_score = score_trend_cluster(members, now=now)["trend_score"]
    solo_score = score_trend_cluster(single, now=now)["trend_score"]
    assert multi_score > solo_score


def test_snapshot_scheduling_by_age() -> None:
    cfg = load_scoring_config()
    assert snapshot_interval_hours(10, config=cfg) == cfg.snapshots.age_0_24h_interval_hours
    assert snapshot_interval_hours(48, config=cfg) == cfg.snapshots.age_1_3d_interval_hours
    assert snapshot_interval_hours(120, config=cfg) == cfg.snapshots.age_3_7d_interval_hours
    assert snapshot_interval_hours(200, config=cfg) is None


def test_is_snapshot_due_without_prior_snapshot() -> None:
    published = datetime.now(UTC) - timedelta(hours=6)
    assert is_snapshot_due(None, published) is True
