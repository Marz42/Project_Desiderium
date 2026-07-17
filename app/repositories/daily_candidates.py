"""Daily candidate repository."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import CreativeAngle, DailyCandidate, LifecycleStatus, PublicationRecord


class DailyCandidateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_date(self, candidate_date: date) -> list[DailyCandidate]:
        stmt = (
            select(DailyCandidate)
            .where(DailyCandidate.date == candidate_date)
            .options(
                selectinload(DailyCandidate.creative_angle)
                .selectinload(CreativeAngle.publication_records)
                .selectinload(PublicationRecord.metric_snapshots),
                selectinload(DailyCandidate.trend),
            )
            .order_by(DailyCandidate.rank)
        )
        return list((await self._session.scalars(stmt)).all())

    async def get_by_angle_and_date(
        self,
        creative_angle_id: uuid.UUID,
        candidate_date: date,
    ) -> DailyCandidate | None:
        stmt = select(DailyCandidate).where(
            DailyCandidate.creative_angle_id == creative_angle_id,
            DailyCandidate.date == candidate_date,
        )
        return await self._session.scalar(stmt)

    async def upsert_candidate(
        self,
        *,
        candidate_date: date,
        creative_angle_id: uuid.UUID,
        trend_id: uuid.UUID,
        rank: int,
        candidate_score: float | None,
        score_snapshot: dict | None,
        trend_score_snapshot: float | None = None,
        lifecycle_status_snapshot: LifecycleStatus | None = None,
        analysis_run_id: uuid.UUID | None = None,
        selected: bool = False,
    ) -> DailyCandidate:
        existing = await self.get_by_angle_and_date(creative_angle_id, candidate_date)
        if existing is not None:
            existing.rank = rank
            existing.candidate_score = candidate_score
            existing.score_snapshot = score_snapshot
            existing.trend_score_snapshot = trend_score_snapshot
            existing.lifecycle_status_snapshot = lifecycle_status_snapshot
            existing.analysis_run_id = analysis_run_id
            await self._session.flush()
            return existing

        row = DailyCandidate(
            date=candidate_date,
            creative_angle_id=creative_angle_id,
            trend_id=trend_id,
            rank=rank,
            candidate_score=candidate_score,
            score_snapshot=score_snapshot,
            trend_score_snapshot=trend_score_snapshot,
            lifecycle_status_snapshot=lifecycle_status_snapshot,
            analysis_run_id=analysis_run_id,
            selected=selected,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def set_selected(
        self,
        candidate_id: uuid.UUID,
        *,
        selected: bool,
    ) -> DailyCandidate | None:
        row = await self._session.get(DailyCandidate, candidate_id)
        if row is None:
            return None
        row.selected = selected
        await self._session.flush()
        return row

    async def list_dates(self, *, limit: int = 60) -> list[date]:
        stmt = (
            select(DailyCandidate.date).distinct().order_by(DailyCandidate.date.desc()).limit(limit)
        )
        return list((await self._session.scalars(stmt)).all())

    async def delete_for_date(self, candidate_date: date) -> None:
        await self._session.execute(
            delete(DailyCandidate).where(DailyCandidate.date == candidate_date)
        )
