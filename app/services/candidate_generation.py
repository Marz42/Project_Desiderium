"""Generate daily candidate snapshots from creative angles."""

from __future__ import annotations

import math
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import AngleStatus, CreativeAngle, LifecycleStatus, TrendTheme
from app.repositories.analysis_runs import AnalysisRunRepository
from app.repositories.daily_candidates import DailyCandidateRepository
from app.services.run_metadata import (
    algorithm_version,
    config_hash,
    load_config_snapshot,
    prompt_versions,
    run_fingerprint,
)
from app.services.scoring_config import get_scoring_config


class CandidateGenerationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._candidates = DailyCandidateRepository(session)
        self._runs = AnalysisRunRepository(session)
        self._config = get_scoring_config()

    async def generate_for_date(
        self,
        candidate_date: date,
        *,
        analysis_run_id: uuid.UUID | None = None,
    ) -> dict:
        snapshot = load_config_snapshot()
        algorithm = algorithm_version()
        snapshot_hash = config_hash(snapshot)
        run = await self._runs.start(
            run_date=candidate_date,
            run_kind="candidate_generation",
            scoring_version=self._config.version,
            algorithm_version=algorithm,
            config_hash=snapshot_hash,
            run_fingerprint=run_fingerprint(
                run_date=candidate_date,
                run_kind="candidate_generation",
                config_hash_value=snapshot_hash,
                algorithm_version_value=algorithm,
            ),
            config_snapshot=snapshot,
            prompt_versions=prompt_versions(),
            analysis_run_id=analysis_run_id,
        )
        angles = await self._load_eligible_angles(candidate_date)
        if not angles:
            summary = {"date": candidate_date.isoformat(), "created": 0, "total": 0}
            await self._runs.finish(run, summary)
            return summary

        ranked = self._rank_angles(angles)
        candidate_config = self._config.candidates
        target = min(candidate_config.target_count, candidate_config.maximum_count)
        max_per_trend = candidate_config.max_angles_per_trend
        max_anime_share = candidate_config.max_anime_share
        min_new_count = math.ceil(target * candidate_config.min_new_trend_share)

        selected: list[tuple[CreativeAngle, float]] = []
        per_trend: dict = {}
        per_anime: dict = {}

        def try_select(angle: CreativeAngle, score: float) -> bool:
            if len(selected) >= target:
                return False
            trend_count = per_trend.get(angle.trend_id, 0)
            if trend_count >= max_per_trend:
                return False
            anime = (angle.trend.anime_title if angle.trend else None) or "_unknown"
            anime_count = per_anime.get(anime, 0)
            if selected and (anime_count + 1) / (len(selected) + 1) > max_anime_share:
                return False
            if angle.status == AngleStatus.BLOCKED:
                return False
            selected.append((angle, score))
            per_trend[angle.trend_id] = trend_count + 1
            per_anime[anime] = anime_count + 1
            return True

        for angle, score in ranked:
            if len(selected) >= min_new_count:
                break
            if angle.trend and angle.trend.lifecycle_status == LifecycleStatus.NEW:
                try_select(angle, score)

        selected_ids = {angle.id for angle, _ in selected}
        for angle, score in ranked:
            if len(selected) >= target:
                break
            if angle.id not in selected_ids and try_select(angle, score):
                selected_ids.add(angle.id)

        await self._candidates.delete_for_date(candidate_date)
        for rank, (angle, score) in enumerate(selected, start=1):
            trend = angle.trend
            await self._candidates.upsert_candidate(
                candidate_date=candidate_date,
                creative_angle_id=angle.id,
                trend_id=angle.trend_id,
                rank=rank,
                candidate_score=score,
                score_snapshot=trend.score_components if trend else None,
                trend_score_snapshot=trend.score if trend else None,
                lifecycle_status_snapshot=trend.lifecycle_status if trend else None,
                analysis_run_id=run.id,
                selected=angle.status == AngleStatus.SELECTED,
            )
        summary = {
            "date": candidate_date.isoformat(),
            "created": len(selected),
            "total": len(angles),
            "new_trend_candidates": len(
                [
                    angle
                    for angle, _ in selected
                    if angle.trend and angle.trend.lifecycle_status == LifecycleStatus.NEW
                ],
            ),
        }
        await self._runs.finish(run, summary)
        return summary

    async def _load_eligible_angles(self, candidate_date: date) -> list[CreativeAngle]:
        stmt = (
            select(CreativeAngle)
            .join(TrendTheme, CreativeAngle.trend_id == TrendTheme.id)
            .where(
                CreativeAngle.generated_date == candidate_date,
                CreativeAngle.status != AngleStatus.BLOCKED,
            )
            .options(selectinload(CreativeAngle.trend))
            .order_by(TrendTheme.score.desc().nullslast(), CreativeAngle.created_at)
        )
        return list((await self._session.scalars(stmt)).all())

    def _rank_angles(self, angles: list[CreativeAngle]) -> list[tuple[CreativeAngle, float]]:
        ranked: list[tuple[CreativeAngle, float]] = []
        for angle in angles:
            trend_score = (
                angle.trend.score if angle.trend and angle.trend.score is not None else 0.0
            )
            ranked.append((angle, float(trend_score)))
        ranked.sort(key=lambda pair: pair[1], reverse=True)
        return ranked
