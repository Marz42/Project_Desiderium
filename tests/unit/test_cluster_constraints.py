"""Tests for G3 hard constraints and lexical embedding."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from app.adapters.embedding.lexical import LexicalEmbeddingProvider
from app.domain.cluster_constraints import cosine_similarity, hard_constraints_allow_merge


def test_anime_conflict_blocks_merge() -> None:
    result = hard_constraints_allow_merge(
        {"anime_title": "One Piece", "entity_id": "a", "topic_type": "event"},
        {"anime_title": "Jujutsu Kaisen", "entity_id": "b", "topic_type": "event"},
    )
    assert result.allowed is False
    assert "anime_title_conflict" in result.reasons


def test_publish_gap_blocks_merge() -> None:
    now = datetime.now(UTC)
    result = hard_constraints_allow_merge(
        {
            "anime_title": "One Piece",
            "entity_id": "a",
            "topic_type": "anime",
            "published_at": now,
        },
        {
            "anime_title": "One Piece",
            "entity_id": "a",
            "topic_type": "anime",
            "published_at": now - timedelta(days=10),
        },
        max_gap_days=7,
    )
    assert result.allowed is False
    assert "publish_gap_exceeded" in result.reasons


def test_protected_trend_blocks_auto_merge() -> None:
    result = hard_constraints_allow_merge(
        {"anime_title": "One Piece", "entity_id": "a", "topic_type": "anime"},
        {
            "anime_title": "One Piece",
            "entity_id": "a",
            "topic_type": "anime",
            "has_brief_or_publication": True,
        },
    )
    assert result.allowed is False
    assert "protected_historical_trend" in result.reasons


def test_lexical_embedding_is_deterministic() -> None:
    provider = LexicalEmbeddingProvider()
    left = asyncio.run(provider.embed("One Piece Egghead Luffy"))
    right = asyncio.run(provider.embed("One Piece Egghead Luffy"))
    assert left.vector == right.vector
    assert cosine_similarity(left.vector, right.vector) > 0.99
