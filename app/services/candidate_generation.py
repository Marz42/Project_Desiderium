"""Generate daily candidate snapshots from creative angles."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import AngleStatus, CreativeAngle, TrendTheme
from app.repositories.daily_candidates import DailyCandidateRepository


TARGET_COUNT = 30
MAX_PER_TREND = 4
MAX_ANIME_SHARE = 0.30


class CandidateGenerationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._candidates = DailyCandidateRepository(session)

    async def generate_for_date(self, candidate_date: date) -> dict:
        angles = await self._load_eligible_angles(candidate_date)
        if not angles:
            return {"date": candidate_date.isoformat(), "created": 0, "total": 0}

        ranked = self._rank_angles(angles)
        target = TARGET_COUNT
        max_per_trend = MAX_PER_TREND
        max_anime_share = MAX_ANIME_SHARE

        selected: list[tuple[CreativeAngle, float]] = []
        per_trend: dict = {}
        per_anime: dict = {}

        for angle, score in ranked:
            if len(selected) >= target:
                break
            trend_count = per_trend.get(angle.trend_id, 0)
            if trend_count >= max_per_trend:
                continue
            anime = (angle.trend.anime_title if angle.trend else None) or "_unknown"
            anime_count = per_anime.get(anime, 0)
            if selected and (anime_count + 1) / (len(selected) + 1) > max_anime_share:
                continue
            if angle.status == AngleStatus.BLOCKED:
                continue
            selected.append((angle, score))
            per_trend[angle.trend_id] = trend_count + 1
            per_anime[anime] = anime_count + 1

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
                selected=angle.status == AngleStatus.SELECTED,
            )

        return {
            "date": candidate_date.isoformat(),
            "created": len(selected),
            "total": len(angles),
        }

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
            trend_score = angle.trend.score if angle.trend and angle.trend.score is not None else 0.0
            ranked.append((angle, float(trend_score)))
        ranked.sort(key=lambda pair: pair[1], reverse=True)
        return ranked
