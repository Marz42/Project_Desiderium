"""Unit tests for YouTube normalization."""

from app.adapters.youtube.normalize import (
    normalize_keyword_external_id,
    normalize_youtube_video,
    parse_iso8601_duration,
)


def test_parse_iso8601_duration():
    assert parse_iso8601_duration("PT1H2M3S") == 3723
    assert parse_iso8601_duration("PT45S") == 45
    assert parse_iso8601_duration(None) is None


def test_normalize_keyword_external_id():
    assert normalize_keyword_external_id("  Anime   Recap ") == "anime recap"


def test_normalize_youtube_video():
    raw = {
        "id": "abc123",
        "snippet": {
            "title": "Test Video",
            "description": "desc",
            "channelId": "UCtest",
            "channelTitle": "Channel",
            "publishedAt": "2026-07-01T12:00:00Z",
            "tags": ["anime"],
            "thumbnails": {"high": {"url": "https://example.com/thumb.jpg"}},
        },
        "statistics": {"viewCount": "1000", "likeCount": "50", "commentCount": "10"},
        "contentDetails": {"duration": "PT5M30S"},
    }
    normalized = normalize_youtube_video(raw)
    assert normalized["external_id"] == "abc123"
    assert normalized["platform"] == "youtube"
    assert normalized["duration_seconds"] == 330
    assert normalized["metrics"]["views"] == 1000
    assert normalized["url"] == "https://www.youtube.com/watch?v=abc123"


def test_normalize_youtube_video_preserves_hidden_likes_as_none():
    normalized = normalize_youtube_video(
        {
            "id": "abc123",
            "snippet": {
                "title": "Hidden likes",
                "publishedAt": "2026-07-17T00:00:00Z",
            },
            "statistics": {"viewCount": "1000", "commentCount": "10"},
            "contentDetails": {"duration": "PT1M"},
        },
    )

    assert normalized["metrics"]["likes"] is None
