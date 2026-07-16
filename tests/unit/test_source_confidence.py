"""Tests for platform source confidence mapping."""

from app.domain.source_confidence import (
    SOURCE_CONFIDENCE_HIGH,
    SOURCE_CONFIDENCE_LOW,
    platform_source_confidence,
)
from app.models import Platform


def test_youtube_high_confidence():
    assert platform_source_confidence(Platform.YOUTUBE) == SOURCE_CONFIDENCE_HIGH


def test_tiktok_low_confidence():
    assert platform_source_confidence(Platform.TIKTOK) == SOURCE_CONFIDENCE_LOW


def test_unknown_platform_defaults_low():
    assert platform_source_confidence("other") == SOURCE_CONFIDENCE_LOW
