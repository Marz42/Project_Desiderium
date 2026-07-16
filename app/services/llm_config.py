"""Load LLM and semantic analysis configuration from YAML."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LLM_CONFIG_PATH = PROJECT_ROOT / "config" / "llm.yaml"
PROMPTS_DIR = PROJECT_ROOT / "config" / "prompts"


@dataclass(frozen=True)
class LlmSettings:
    base_url: str
    model: str
    timeout_seconds: float
    max_retries: int
    retry_backoff_seconds: float
    temperature: float
    max_output_tokens: int


@dataclass(frozen=True)
class TranscriptSettings:
    max_text_chars: int
    excerpt_chars: int
    summary_cache_ttl_seconds: int
    preferred_languages: tuple[str, ...]


@dataclass(frozen=True)
class SemanticSettings:
    max_angles_per_trend: int
    min_angles_per_trend: int
    dedup_similarity_threshold: float
    low_confidence_threshold: float
    max_evidence_videos_per_request: int


@dataclass(frozen=True)
class LlmConfig:
    llm: LlmSettings
    transcripts: TranscriptSettings
    semantic: SemanticSettings


@dataclass(frozen=True)
class PromptTemplate:
    version: str
    name: str
    description: str
    system: str
    user_template: str
    output_schema: dict[str, Any]


def _section(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"config section '{key}' must be a mapping")
    return value


def load_llm_config(path: Path | None = None) -> LlmConfig:
    config_path = path or DEFAULT_LLM_CONFIG_PATH
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("llm config root must be a mapping")

    llm = _section(raw, "llm")
    transcripts = _section(raw, "transcripts")
    semantic = _section(raw, "semantic")

    return LlmConfig(
        llm=LlmSettings(
            base_url=str(llm["base_url"]),
            model=str(llm["model"]),
            timeout_seconds=float(llm["timeout_seconds"]),
            max_retries=int(llm["max_retries"]),
            retry_backoff_seconds=float(llm["retry_backoff_seconds"]),
            temperature=float(llm["temperature"]),
            max_output_tokens=int(llm["max_output_tokens"]),
        ),
        transcripts=TranscriptSettings(
            max_text_chars=int(transcripts["max_text_chars"]),
            excerpt_chars=int(transcripts["excerpt_chars"]),
            summary_cache_ttl_seconds=int(transcripts["summary_cache_ttl_seconds"]),
            preferred_languages=tuple(str(lang) for lang in transcripts["preferred_languages"]),
        ),
        semantic=SemanticSettings(
            max_angles_per_trend=int(semantic["max_angles_per_trend"]),
            min_angles_per_trend=int(semantic["min_angles_per_trend"]),
            dedup_similarity_threshold=float(semantic["dedup_similarity_threshold"]),
            low_confidence_threshold=float(semantic["low_confidence_threshold"]),
            max_evidence_videos_per_request=int(semantic["max_evidence_videos_per_request"]),
        ),
    )


def load_prompt_template(name: str, *, prompts_dir: Path | None = None) -> PromptTemplate:
    directory = prompts_dir or PROMPTS_DIR
    matches = sorted(directory.glob(f"{name}_v*.yaml"))
    if not matches:
        raise FileNotFoundError(f"prompt template not found: {name}")
    path = matches[-1]
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"prompt {path.name} root must be a mapping")
    return PromptTemplate(
        version=str(raw["version"]),
        name=str(raw["name"]),
        description=str(raw.get("description") or ""),
        system=str(raw["system"]),
        user_template=str(raw["user_template"]),
        output_schema=dict(raw["output_schema"]),
    )


@lru_cache
def get_llm_config() -> LlmConfig:
    return load_llm_config()
