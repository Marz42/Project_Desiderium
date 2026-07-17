"""Unit tests for shadow validation scoring."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from scripts.shadow.scoring import (
    VideoRecord,
    assign_age_bucket,
    breakout_ratio,
    cold_start_velocity,
    compute_channel_baselines,
    global_baseline_by_bucket,
    score_trend_cluster,
)


def _video(
    video_id: str,
    channel_id: str,
    views: int,
    hours_ago: float,
    *,
    tier: str = "priority",
    title: str = "test",
) -> VideoRecord:
    return VideoRecord(
        video_id=video_id,
        channel_id=channel_id,
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
    assert cold_start_velocity(1000, 0.5) == 500.0


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
    hot = next(v for v in videos if v.video_id == "hot")
    result = breakout_ratio(hot, baselines, fallback, now=now)
    assert result["breakout_ratio"] > 2.0
    assert result["baseline_source"] == "channel_median"


def test_large_channel_routine_video_scores_lower() -> None:
    now = datetime.now(UTC)
    videos = [
        _video("r1", "big", 100000, 12),
        _video("r2", "big", 110000, 12),
        _video("r3", "big", 105000, 12),
        _video("routine", "big", 108000, 12),
    ]
    baselines = compute_channel_baselines(videos, now=now)
    fallback = global_baseline_by_bucket(videos, now=now)
    routine = next(v for v in videos if v.video_id == "routine")
    result = breakout_ratio(routine, baselines, fallback, now=now)
    assert result["breakout_ratio"] < 1.5


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
