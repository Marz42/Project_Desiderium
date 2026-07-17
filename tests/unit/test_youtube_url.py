"""Unit tests for YouTube video ID parsing (G4 published URL workflow)."""

from __future__ import annotations

import pytest

from app.domain.youtube_url import parse_youtube_video_id

VALID_ID = "dQw4w9WgXcQ"


@pytest.mark.parametrize(
    "url",
    [
        f"https://www.youtube.com/watch?v={VALID_ID}",
        f"https://youtube.com/watch?v={VALID_ID}",
        f"https://m.youtube.com/watch?v={VALID_ID}",
        f"http://www.youtube.com/watch?v={VALID_ID}&t=30s",
        f"https://youtu.be/{VALID_ID}",
        f"https://youtu.be/{VALID_ID}?t=5",
        f"https://www.youtube.com/shorts/{VALID_ID}",
        f"https://www.youtube.com/embed/{VALID_ID}",
        f"https://www.youtube-nocookie.com/embed/{VALID_ID}",
        f"www.youtube.com/watch?v={VALID_ID}",
        f"  https://youtu.be/{VALID_ID}  ",
    ],
)
def test_parses_valid_video_id_from_supported_url_forms(url: str) -> None:
    assert parse_youtube_video_id(url) == VALID_ID


@pytest.mark.parametrize(
    "url",
    [
        None,
        "",
        "   ",
        "not a url",
        "https://vimeo.com/12345678",
        "https://www.youtube.com/watch?v=short",
        "https://www.youtube.com/watch",
        "https://www.youtube.com/",
        "https://youtu.be/",
        "https://www.youtube.com/channel/UC123456789",
        f"https://evil.com/watch?v={VALID_ID}",
    ],
)
def test_rejects_missing_or_unsupported_urls(url: str | None) -> None:
    assert parse_youtube_video_id(url) is None
