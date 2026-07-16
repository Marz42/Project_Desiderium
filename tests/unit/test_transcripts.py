"""Unit tests for transcript service metadata fallback."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.models import ContentItem, Platform
from app.services.transcripts import TranscriptService


def test_build_excerpt_uses_metadata_when_no_transcript() -> None:
    service = TranscriptService.__new__(TranscriptService)
    from app.services.llm_config import get_llm_config

    service._config = get_llm_config()  # type: ignore[attr-defined]
    service._summary_cache = {}  # type: ignore[attr-defined]

    item = ContentItem(
        id=uuid.uuid4(),
        platform=Platform.YOUTUBE,
        external_id="abc123",
        title_original="One Piece Egghead Recap",
        description="Luffy fights the Gorosei",
        tags=["anime", "recap"],
        duration_seconds=480,
        published_at=datetime.now(UTC),
    )
    excerpt = service.build_excerpt(item, None)
    assert excerpt.has_captions is False
    assert excerpt.source == "metadata"
    assert excerpt.confidence < 0.5
    assert "One Piece" in excerpt.text


def test_build_excerpt_truncates_long_transcript() -> None:
    service = TranscriptService.__new__(TranscriptService)
    from app.services.llm_config import get_llm_config

    service._config = get_llm_config()  # type: ignore[attr-defined]
    service._summary_cache = {}  # type: ignore[attr-defined]

    item = ContentItem(
        id=uuid.uuid4(),
        platform=Platform.YOUTUBE,
        external_id="abc123",
        title_original="Test",
        published_at=datetime.now(UTC),
    )
    long_text = "word " * 5000
    excerpt = service.build_excerpt(item, long_text)
    assert excerpt.has_captions is True
    assert len(excerpt.text) <= service._config.transcripts.excerpt_chars + 1
