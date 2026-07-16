"""Trend cluster scoring service."""

from __future__ import annotations

from typing import Any

from app.domain.trend_metrics import score_trend_cluster
from app.services.scoring_config import ScoringConfig, get_scoring_config


class TrendScoringService:
    def __init__(self, config: ScoringConfig | None = None) -> None:
        self._config = config or get_scoring_config()

    def score_cluster(self, members: list[dict[str, Any]]) -> dict[str, Any]:
        return score_trend_cluster(members, config=self._config)
