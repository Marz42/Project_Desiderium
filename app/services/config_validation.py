"""Fail-fast validation for runtime YAML and production secrets."""

from __future__ import annotations

import math

from app.config import Settings
from app.services.llm_config import get_llm_config, load_prompt_template
from app.services.run_metadata import PROMPT_NAMES
from app.services.scoring_config import get_entity_dictionary, get_scoring_config


def validate_runtime_config(settings: Settings) -> None:
    scoring = get_scoring_config()
    llm = get_llm_config()
    get_entity_dictionary()

    weights = (
        scoring.weights.channel_resonance,
        scoring.weights.relative_breakout,
        scoring.weights.momentum,
        scoring.weights.persistence,
        scoring.weights.absolute_scale,
        scoring.weights.novelty,
    )
    if not math.isclose(sum(weights), 1.0, abs_tol=1e-9):
        raise ValueError("scoring weights must sum to 1.0")
    if scoring.thresholds.rising_ratio <= scoring.thresholds.declining_ratio:
        raise ValueError("rising_ratio must be greater than declining_ratio")
    if scoring.thresholds.strong_breakout < scoring.thresholds.breakout:
        raise ValueError("strong_breakout must be >= breakout")

    candidates = scoring.candidates
    if candidates.target_count <= 0 or candidates.maximum_count < candidates.target_count:
        raise ValueError("candidate counts must be positive and maximum_count >= target_count")
    if candidates.max_angles_per_trend <= 0:
        raise ValueError("max_angles_per_trend must be positive")
    if not 0 < candidates.max_anime_share <= 1:
        raise ValueError("max_anime_share must be in (0, 1]")
    if not 0 <= candidates.min_new_trend_share <= 1:
        raise ValueError("min_new_trend_share must be in [0, 1]")
    if llm.semantic.max_angles_per_trend != candidates.max_angles_per_trend:
        raise ValueError("semantic and candidate max_angles_per_trend must match")
    if llm.transcripts.unavailable_retry_days < 1:
        raise ValueError("unavailable_retry_days must be positive")

    publication = scoring.publication
    if len(publication.windows_hours) != 4:
        raise ValueError("publication.windows_hours must have exactly 4 entries")
    if list(publication.windows_hours) != sorted(publication.windows_hours):
        raise ValueError("publication.windows_hours must be strictly ascending")
    if publication.windows_hours[0] != 0:
        raise ValueError("publication.windows_hours must start at 0 (initial window)")
    if publication.late_backfill_grace_hours < 0:
        raise ValueError("publication.late_backfill_grace_hours must be non-negative")
    if not publication.baseline_version:
        raise ValueError("publication.baseline_version is required")
    if publication.max_consecutive_failures < 1:
        raise ValueError("publication.max_consecutive_failures must be positive")
    if publication.retry_backoff_hours <= 0:
        raise ValueError("publication.retry_backoff_hours must be positive")

    clustering = scoring.clustering
    if clustering.recall_top_k < 1:
        raise ValueError("clustering.recall_top_k must be positive")
    if not 0 <= clustering.low_similarity < clustering.high_similarity <= 1:
        raise ValueError("clustering similarity thresholds must satisfy 0 <= low < high <= 1")
    if not 0 <= clustering.llm_min_confidence <= 1:
        raise ValueError("clustering.llm_min_confidence must be in [0, 1]")
    if clustering.embedding.provider not in {"local_onnx", "remote_api", "lexical"}:
        raise ValueError("clustering.embedding.provider must be local_onnx, remote_api, or lexical")
    if not clustering.embedding.embedding_space:
        raise ValueError("clustering.embedding.embedding_space is required")

    for prompt_name in PROMPT_NAMES:
        prompt = load_prompt_template(prompt_name)
        if not prompt.version or prompt.output_schema.get("type") != "object":
            raise ValueError(f"invalid prompt template: {prompt_name}")

    if settings.environment.lower() == "production":
        if settings.secret_key == "change-me-in-production" or len(settings.secret_key) < 32:
            raise ValueError("production SECRET_KEY must be non-default and at least 32 characters")
        if not settings.manager_password:
            raise ValueError("production MANAGER_PASSWORD is required")
        if settings.tiktok_enabled and not settings.tiktok_cookie:
            raise ValueError("TIKTOK_COOKIE is required when TikTok is enabled")
