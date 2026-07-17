"""Build reproducibility metadata for analysis runs."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import yaml

from app.services.llm_config import PROMPTS_DIR, load_prompt_template
from app.services.scoring_config import DEFAULT_SCORING_PATH

PROMPT_NAMES = (
    "title_translation",
    "trend_naming",
    "why_trending",
    "creative_angles",
    "format_classification",
    "cluster_adjudication",
)


def algorithm_version() -> str:
    try:
        return version("desiderium")
    except PackageNotFoundError:
        return "development"


def load_config_snapshot(path: Path = DEFAULT_SCORING_PATH) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("scoring config root must be a mapping")
    return raw


def config_hash(snapshot: dict[str, Any]) -> str:
    canonical = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def run_fingerprint(
    *,
    run_date: date,
    run_kind: str,
    config_hash_value: str,
    algorithm_version_value: str,
) -> str:
    payload = {
        "run_date": run_date.isoformat(),
        "run_kind": run_kind,
        "config_hash": config_hash_value,
        "algorithm_version": algorithm_version_value,
    }
    return config_hash(payload)


def prompt_versions(prompts_dir: Path = PROMPTS_DIR) -> dict[str, str]:
    return {
        name: load_prompt_template(name, prompts_dir=prompts_dir).version for name in PROMPT_NAMES
    }
