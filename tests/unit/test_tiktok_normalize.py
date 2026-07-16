"""Tests for TikTok normalization."""

from app.adapters.tiktok.normalize import (
    normalize_account_external_id,
    normalize_keyword_external_id,
    normalize_tiktok_video,
)
from app.domain.source_confidence import SOURCE_CONFIDENCE_LOW


def test_normalize_keyword_external_id():
    assert normalize_keyword_external_id("  Anime  Edit  ") == "anime edit"


def test_normalize_account_external_id():
    assert normalize_account_external_id("@Creator") == "creator"


def test_normalize_tiktok_video_source_confidence():
    raw = {
        "id": "7123456789012345678",
        "desc": "#onepiece fan edit",
        "createTime": 1710000000,
        "author": {"id": "1", "uniqueId": "fan", "nickname": "Fan"},
        "stats": {"playCount": 500, "diggCount": 20},
        "video": {"cover": "https://example.com/t.jpg"},
        "duration": 30,
    }
    normalized = normalize_tiktok_video(raw, selector_version="v1")
    assert normalized["platform"] == "tiktok"
    assert normalized["source_confidence"] == SOURCE_CONFIDENCE_LOW
    assert normalized["metrics"]["views"] == 500
    assert normalized["tags"] == ["onepiece"]
    assert normalized["raw_payload"]["_meta"]["source_confidence"] == SOURCE_CONFIDENCE_LOW
