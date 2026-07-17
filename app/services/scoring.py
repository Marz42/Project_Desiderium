"""Trend cluster scoring service."""

from __future__ import annotations

from typing import Any

from app.domain.trend_metrics import score_trend_cluster
from app.services.scoring_config import ScoringConfig, get_scoring_config


class TrendScoringService:
    def __init__(self, config: ScoringConfig | None = None) -> None:
        self._config = config or get_scoring_config()

    def score_cluster(self, members: list[dict[str, Any]]) -> dict[str, Any]:
        score = score_trend_cluster(members, config=self._config)
        if not members:
            return score
        multiplier = sum(
            float(member.get("relevance_multiplier", 1.0)) for member in members
        ) / len(
            members,
        )
        raw_score = float(score.get("trend_score", 0.0))
        score["raw_trend_score"] = raw_score
        score["relevance_multiplier"] = round(multiplier, 3)
        score["trend_score"] = round(raw_score * multiplier, 2)
        return score
