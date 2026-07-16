"""Platform source confidence labels for ingested content."""

from __future__ import annotations

from app.models import Platform

SOURCE_CONFIDENCE_HIGH = "high"
SOURCE_CONFIDENCE_LOW = "low"

_PLATFORM_CONFIDENCE: dict[Platform, str] = {
    Platform.YOUTUBE: SOURCE_CONFIDENCE_HIGH,
    Platform.TIKTOK: SOURCE_CONFIDENCE_LOW,
}


def platform_source_confidence(platform: Platform | str) -> str:
    if isinstance(platform, str):
        try:
            platform = Platform(platform)
        except ValueError:
            return SOURCE_CONFIDENCE_LOW
    return _PLATFORM_CONFIDENCE.get(platform, SOURCE_CONFIDENCE_LOW)
