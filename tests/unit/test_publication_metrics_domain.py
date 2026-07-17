"""Unit tests for pure G4 publication metrics calculations (no DB, no HTTP)."""

from __future__ import annotations

from app.domain.publication_metrics import (
    classify_format,
    compute_performance_ratio,
    is_late_backfill,
    is_window_due,
    median_velocity,
)
from app.models import CreativeFormat


def test_classify_format_short_for_videos_under_three_minutes() -> None:
    assert classify_format(60) == CreativeFormat.SHORT
    assert classify_format(180) == CreativeFormat.SHORT


def test_classify_format_long_for_videos_over_three_minutes() -> None:
    assert classify_format(181) == CreativeFormat.LONG
    assert classify_format(3600) == CreativeFormat.LONG


def test_classify_format_defaults_to_long_when_duration_unknown() -> None:
    assert classify_format(None) == CreativeFormat.LONG


def test_window_due_when_age_meets_or_exceeds_target() -> None:
    assert is_window_due(24.0, 24.0) is True
    assert is_window_due(24.1, 24.0) is True


def test_window_not_due_before_target_age() -> None:
    assert is_window_due(23.9, 24.0) is False


def test_initial_window_is_always_immediately_due() -> None:
    assert is_window_due(0.0, 0.0) is True


def test_late_backfill_flag_respects_grace_period() -> None:
    assert is_late_backfill(30.0, 24.0, 6.0) is False
    assert is_late_backfill(30.1, 24.0, 6.0) is True
    assert is_late_backfill(1000.0, 24.0, 6.0) is True


def test_median_velocity_returns_none_for_empty_samples() -> None:
    assert median_velocity([], min_age_hours=0.5) is None


def test_median_velocity_computes_median_of_views_per_hour() -> None:
    samples = [(100.0, 10.0), (200.0, 10.0), (600.0, 10.0)]
    assert median_velocity(samples, min_age_hours=0.5) == 20.0


def test_median_velocity_guards_against_near_zero_age() -> None:
    samples = [(100.0, 0.0)]
    velocity = median_velocity(samples, min_age_hours=0.5)
    assert velocity == 200.0


def test_compute_performance_ratio_above_baseline() -> None:
    ratio = compute_performance_ratio(velocity=150.0, baseline_velocity=100.0, epsilon=0.01)
    assert ratio == 1.5


def test_compute_performance_ratio_below_baseline() -> None:
    ratio = compute_performance_ratio(velocity=50.0, baseline_velocity=100.0, epsilon=0.01)
    assert ratio == 0.5


def test_compute_performance_ratio_guards_against_zero_baseline() -> None:
    ratio = compute_performance_ratio(velocity=50.0, baseline_velocity=0.0, epsilon=0.01)
    assert ratio == 5000.0
