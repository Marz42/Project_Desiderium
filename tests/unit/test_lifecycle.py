"""Unit tests for lifecycle status transitions."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.models import LifecycleStatus
from app.services.lifecycle import determine_lifecycle_status


def test_new_trend_within_24h() -> None:
    status = determine_lifecycle_status(
        first_detected_at=datetime.now(UTC) - timedelta(hours=6),
        previous_status=None,
        growth_ratio=1.0,
        activity_last_24h=50.0,
        latest_video_age_hours=12.0,
    )
    assert status == LifecycleStatus.NEW


def test_rising_when_growth_high() -> None:
    status = determine_lifecycle_status(
        first_detected_at=datetime.now(UTC) - timedelta(days=3),
        previous_status=LifecycleStatus.STABLE,
        growth_ratio=1.5,
        activity_last_24h=80.0,
        latest_video_age_hours=10.0,
    )
    assert status == LifecycleStatus.RISING


def test_declining_when_growth_low() -> None:
    status = determine_lifecycle_status(
        first_detected_at=datetime.now(UTC) - timedelta(days=5),
        previous_status=LifecycleStatus.STABLE,
        growth_ratio=0.5,
        activity_last_24h=20.0,
        latest_video_age_hours=10.0,
    )
    assert status == LifecycleStatus.DECLINING
