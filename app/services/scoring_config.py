"""Load trend scoring and entity configuration from YAML files."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCORING_PATH = PROJECT_ROOT / "config" / "scoring.yaml"
DEFAULT_ENTITIES_PATH = PROJECT_ROOT / "config" / "anime_entities.yaml"


@dataclass(frozen=True)
class ScoringWeights:
    channel_resonance: float
    relative_breakout: float
    momentum: float
    persistence: float
    absolute_scale: float
    novelty: float


@dataclass(frozen=True)
class ThresholdConfig:
    breakout: float
    strong_breakout: float
    below_average: float
    normal: float
    above_average: float
    rising_ratio: float
    declining_ratio: float
    reviving_ratio: float
    standard_min_channels_72h: int
    standard_breakout_ge_2_pct: float
    early_min_channels_24h: int
    early_min_videos_24h: int
    dormant_hours_no_video: int
    min_cluster_members: int
    min_cluster_channels: int


@dataclass(frozen=True)
class ChannelWeights:
    priority: float
    general: float
    experimental: float


@dataclass(frozen=True)
class BaselineConfig:
    sample_size: int
    confidence_high_min: int
    confidence_medium_min: int
    confidence_low_min: int


@dataclass(frozen=True)
class SnapshotScheduleConfig:
    age_0_24h_interval_hours: float
    age_1_3d_interval_hours: float
    age_3_7d_interval_hours: float
    lookback_days: int
    retention_days: int


@dataclass(frozen=True)
class MomentumConfig:
    recent_24h_multiplier: float
    recent_72h_multiplier: float
    persistence_channel_multiplier: float
    absolute_scale_log_multiplier: float


@dataclass(frozen=True)
class NoveltyConfig:
    fresh_24h_score: float
    fresh_72h_score: float
    fresh_7d_score: float
    fresh_default_score: float
    fresh_24h_min_videos: int
    fresh_72h_min_videos: int


@dataclass(frozen=True)
class RelativeBreakoutConfig:
    median_weight: float
    pct_ge_2_weight: float
    pct_ge_2_scale: float


@dataclass(frozen=True)
class LifecycleConfig:
    new_max_age_hours: float
    dormant_activity_threshold: float


@dataclass(frozen=True)
class CandidateConfig:
    target_count: int
    maximum_count: int
    max_angles_per_trend: int
    max_anime_share: float
    min_new_trend_share: float


@dataclass(frozen=True)
class RelevanceConfig:
    allowed_language_prefixes: tuple[str, ...]
    unknown_language_policy: str
    excluded_language_keywords: tuple[str, ...]
    excluded_topic_keywords: tuple[str, ...]
    generic_topic_keywords: tuple[str, ...]
    excluded_score_multiplier: float
    generic_score_multiplier: float


@dataclass(frozen=True)
class PublicationConfig:
    team_channel_ids: tuple[str, ...]
    windows_hours: tuple[int, ...]
    late_backfill_grace_hours: float
    baseline_version: str
    max_consecutive_failures: int
    retry_backoff_hours: float


@dataclass(frozen=True)
class EmbeddingProviderConfig:
    provider: str
    embedding_space: str
    model_name: str
    model_revision: str
    remote_base_url: str
    remote_model: str
    allow_lexical_fallback: bool
    cache_enabled: bool


@dataclass(frozen=True)
class ClusteringConfig:
    enabled: bool
    max_publish_gap_days: int
    recall_top_k: int
    high_similarity: float
    low_similarity: float
    llm_min_confidence: float
    embedding: EmbeddingProviderConfig


@dataclass(frozen=True)
class ScoringConfig:
    version: str
    weights: ScoringWeights
    thresholds: ThresholdConfig
    channels: ChannelWeights
    baselines: BaselineConfig
    snapshots: SnapshotScheduleConfig
    momentum: MomentumConfig
    novelty: NoveltyConfig
    relative_breakout: RelativeBreakoutConfig
    lifecycle: LifecycleConfig
    candidates: CandidateConfig
    relevance: RelevanceConfig
    clustering: ClusteringConfig
    publication: PublicationConfig
    target_channel_count: float
    capped_breakout_max: float
    epsilon: float
    min_age_hours: float


@dataclass(frozen=True)
class EntityRule:
    entity_id: str
    canonical_name: str
    anime_title: str
    topic_type: str
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class EntityDictionary:
    entities: tuple[EntityRule, ...]


def _section(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"config section '{key}' must be a mapping")
    return value


def load_scoring_config(path: Path | None = None) -> ScoringConfig:
    config_path = path or DEFAULT_SCORING_PATH
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("scoring config root must be a mapping")

    scoring = _section(raw, "scoring")
    thresholds = _section(raw, "thresholds")
    channels = _section(raw, "channels")
    baselines = _section(raw, "baselines")
    snapshots = _section(raw, "snapshots")
    momentum = _section(raw, "momentum")
    novelty = _section(raw, "novelty")
    relative_breakout = _section(raw, "relative_breakout")
    lifecycle = _section(raw, "lifecycle")
    candidates = _section(raw, "candidates")
    relevance = _section(raw, "relevance")
    publication = raw.get("publication") or {}
    if not isinstance(publication, dict):
        raise ValueError("config section 'publication' must be a mapping")
    clustering_raw = raw.get("clustering") or {}
    if not isinstance(clustering_raw, dict):
        raise ValueError("config section 'clustering' must be a mapping")
    embedding_raw = clustering_raw.get("embedding") or {}
    if not isinstance(embedding_raw, dict):
        raise ValueError("config section 'clustering.embedding' must be a mapping")

    return ScoringConfig(
        version=str(raw["version"]),
        weights=ScoringWeights(
            channel_resonance=float(scoring["channel_resonance_weight"]),
            relative_breakout=float(scoring["relative_breakout_weight"]),
            momentum=float(scoring["momentum_weight"]),
            persistence=float(scoring["persistence_weight"]),
            absolute_scale=float(scoring["absolute_scale_weight"]),
            novelty=float(scoring["novelty_weight"]),
        ),
        thresholds=ThresholdConfig(
            breakout=float(thresholds["breakout"]),
            strong_breakout=float(thresholds["strong_breakout"]),
            below_average=float(thresholds["below_average"]),
            normal=float(thresholds["normal"]),
            above_average=float(thresholds["above_average"]),
            rising_ratio=float(thresholds["rising_ratio"]),
            declining_ratio=float(thresholds["declining_ratio"]),
            reviving_ratio=float(thresholds["reviving_ratio"]),
            standard_min_channels_72h=int(
                thresholds.get(
                    "standard_min_channels_72h",
                    thresholds.get("standard_min_videos_72h", 3),
                ),
            ),
            standard_breakout_ge_2_pct=float(thresholds["standard_breakout_ge_2_pct"]),
            early_min_channels_24h=int(
                thresholds.get(
                    "early_min_channels_24h",
                    thresholds.get("early_min_videos_24h", 2),
                ),
            ),
            early_min_videos_24h=int(thresholds["early_min_videos_24h"]),
            dormant_hours_no_video=int(thresholds["dormant_hours_no_video"]),
            min_cluster_members=int(thresholds["min_cluster_members"]),
            min_cluster_channels=int(thresholds["min_cluster_channels"]),
        ),
        channels=ChannelWeights(
            priority=float(channels["priority_weight"]),
            general=float(channels["general_weight"]),
            experimental=float(channels["experimental_weight"]),
        ),
        baselines=BaselineConfig(
            sample_size=int(baselines["sample_size"]),
            confidence_high_min=int(baselines["confidence_high_min"]),
            confidence_medium_min=int(baselines["confidence_medium_min"]),
            confidence_low_min=int(baselines["confidence_low_min"]),
        ),
        snapshots=SnapshotScheduleConfig(
            age_0_24h_interval_hours=float(snapshots["age_0_24h_interval_hours"]),
            age_1_3d_interval_hours=float(snapshots["age_1_3d_interval_hours"]),
            age_3_7d_interval_hours=float(snapshots["age_3_7d_interval_hours"]),
            lookback_days=int(snapshots["lookback_days"]),
            retention_days=int(snapshots.get("retention_days", 90)),
        ),
        momentum=MomentumConfig(
            recent_24h_multiplier=float(momentum["recent_24h_multiplier"]),
            recent_72h_multiplier=float(momentum["recent_72h_multiplier"]),
            persistence_channel_multiplier=float(momentum["persistence_channel_multiplier"]),
            absolute_scale_log_multiplier=float(momentum["absolute_scale_log_multiplier"]),
        ),
        novelty=NoveltyConfig(
            fresh_24h_score=float(novelty["fresh_24h_score"]),
            fresh_72h_score=float(novelty["fresh_72h_score"]),
            fresh_7d_score=float(novelty["fresh_7d_score"]),
            fresh_default_score=float(novelty["fresh_default_score"]),
            fresh_24h_min_videos=int(novelty["fresh_24h_min_videos"]),
            fresh_72h_min_videos=int(novelty["fresh_72h_min_videos"]),
        ),
        relative_breakout=RelativeBreakoutConfig(
            median_weight=float(relative_breakout["median_weight"]),
            pct_ge_2_weight=float(relative_breakout["pct_ge_2_weight"]),
            pct_ge_2_scale=float(relative_breakout["pct_ge_2_scale"]),
        ),
        lifecycle=LifecycleConfig(
            new_max_age_hours=float(lifecycle["new_max_age_hours"]),
            dormant_activity_threshold=float(lifecycle["dormant_activity_threshold"]),
        ),
        candidates=CandidateConfig(
            target_count=int(candidates["target_count"]),
            maximum_count=int(candidates["maximum_count"]),
            max_angles_per_trend=int(candidates["max_angles_per_trend"]),
            max_anime_share=float(candidates["max_anime_share"]),
            min_new_trend_share=float(candidates["min_new_trend_share"]),
        ),
        relevance=RelevanceConfig(
            allowed_language_prefixes=tuple(
                str(value).lower() for value in relevance["allowed_language_prefixes"]
            ),
            unknown_language_policy=str(relevance["unknown_language_policy"]),
            excluded_language_keywords=tuple(
                str(value).lower() for value in relevance["excluded_language_keywords"]
            ),
            excluded_topic_keywords=tuple(
                str(value).lower() for value in relevance["excluded_topic_keywords"]
            ),
            generic_topic_keywords=tuple(
                str(value).lower() for value in relevance["generic_topic_keywords"]
            ),
            excluded_score_multiplier=float(relevance["excluded_score_multiplier"]),
            generic_score_multiplier=float(relevance["generic_score_multiplier"]),
        ),
        clustering=ClusteringConfig(
            enabled=bool(clustering_raw.get("enabled", True)),
            max_publish_gap_days=int(clustering_raw.get("max_publish_gap_days", 7)),
            recall_top_k=int(clustering_raw.get("recall_top_k", 5)),
            high_similarity=float(clustering_raw.get("high_similarity", 0.88)),
            low_similarity=float(clustering_raw.get("low_similarity", 0.72)),
            llm_min_confidence=float(clustering_raw.get("llm_min_confidence", 0.80)),
            embedding=EmbeddingProviderConfig(
                provider=str(embedding_raw.get("provider", "lexical")),
                embedding_space=str(
                    embedding_raw.get("embedding_space", "lexical:char-ngram-v1"),
                ),
                model_name=str(
                    embedding_raw.get("model_name", "sentence-transformers/all-MiniLM-L6-v2"),
                ),
                model_revision=str(embedding_raw.get("model_revision", "main")),
                remote_base_url=str(embedding_raw.get("remote_base_url") or ""),
                remote_model=str(embedding_raw.get("remote_model") or ""),
                allow_lexical_fallback=bool(embedding_raw.get("allow_lexical_fallback", True)),
                cache_enabled=bool(embedding_raw.get("cache_enabled", True)),
            ),
        ),
        publication=PublicationConfig(
            team_channel_ids=tuple(
                str(value) for value in publication.get("team_channel_ids") or []
            ),
            windows_hours=tuple(
                int(value) for value in publication.get("windows_hours") or [0, 24, 72, 168]
            ),
            late_backfill_grace_hours=float(publication.get("late_backfill_grace_hours", 6)),
            baseline_version=str(
                publication.get("baseline_version", "publication-velocity-v1"),
            ),
            max_consecutive_failures=int(publication.get("max_consecutive_failures", 3)),
            retry_backoff_hours=float(publication.get("retry_backoff_hours", 24)),
        ),
        target_channel_count=float(scoring["target_channel_count"]),
        capped_breakout_max=float(scoring["capped_breakout_max"]),
        epsilon=float(scoring["epsilon"]),
        min_age_hours=float(scoring["min_age_hours"]),
    )


def load_entity_dictionary(path: Path | None = None) -> EntityDictionary:
    config_path = path or DEFAULT_ENTITIES_PATH
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("entity config root must be a mapping")
    entries = raw.get("entities") or []
    entities: list[EntityRule] = []
    for entry in entries:
        entities.append(
            EntityRule(
                entity_id=str(entry["entity_id"]),
                canonical_name=str(entry["canonical_name"]),
                anime_title=str(entry.get("anime_title") or ""),
                topic_type=str(entry.get("topic_type") or "anime"),
                keywords=tuple(str(kw) for kw in entry.get("keywords") or []),
            )
        )
    return EntityDictionary(entities=tuple(entities))


@lru_cache
def get_scoring_config() -> ScoringConfig:
    return load_scoring_config()


@lru_cache
def get_entity_dictionary() -> EntityDictionary:
    return load_entity_dictionary()
