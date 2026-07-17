"""Target-market relevance classification tests."""

from __future__ import annotations

from app.services.relevance import classify_relevance
from app.services.scoring_config import get_scoring_config


def classify(title: str, language: str | None = None):
    return classify_relevance(
        title=title,
        language=language,
        config=get_scoring_config().relevance,
    )


def test_target_english_anime_is_allowed() -> None:
    result = classify("Solo Leveling Jinwoo Explained", "en-US")
    assert result.category == "target"
    assert result.multiplier == 1.0


def test_hindi_audio_or_title_is_excluded() -> None:
    assert classify("Anime recap", "hi").multiplier == 0
    assert classify("Jujutsu Kaisen in Hindi", None).multiplier == 0


def test_manhwa_is_excluded_and_generic_lists_are_penalized() -> None:
    assert classify("Overpowered Manhwa Hero", "en").multiplier == 0
    result = classify("Top 10 Anime You Must Watch", "en")
    assert result.category == "generic_topic"
    assert 0 < result.multiplier < 1
