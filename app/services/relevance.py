"""Conservative target-market relevance classification."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.scoring_config import RelevanceConfig


@dataclass(frozen=True)
class RelevanceResult:
    category: str
    multiplier: float
    reason: str


def classify_relevance(
    *,
    title: str,
    language: str | None,
    config: RelevanceConfig,
) -> RelevanceResult:
    normalized_title = title.casefold()
    normalized_language = (language or "").casefold()

    if normalized_language and not any(
        normalized_language.startswith(prefix) for prefix in config.allowed_language_prefixes
    ):
        return RelevanceResult(
            "excluded_language", config.excluded_score_multiplier, normalized_language
        )
    if any(keyword.casefold() in normalized_title for keyword in config.excluded_language_keywords):
        return RelevanceResult(
            "excluded_language", config.excluded_score_multiplier, "title keyword"
        )
    if any(keyword.casefold() in normalized_title for keyword in config.excluded_topic_keywords):
        return RelevanceResult("excluded_topic", config.excluded_score_multiplier, "adjacent topic")
    if any(keyword.casefold() in normalized_title for keyword in config.generic_topic_keywords):
        return RelevanceResult("generic_topic", config.generic_score_multiplier, "generic topic")
    if not normalized_language and config.unknown_language_policy == "exclude":
        return RelevanceResult(
            "unknown_language", config.excluded_score_multiplier, "language missing"
        )
    return RelevanceResult("target", 1.0, "target market")
