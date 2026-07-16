"""Admin UI data for today's candidates page."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import AngleStatus, CreativeAngle, CreativeFormat, DailyCandidate, LifecycleStatus, TrendTheme, WatchTier
from app.repositories.content import ContentRepository
from app.repositories.creative_angles import CreativeAngleRepository
from app.repositories.daily_candidates import DailyCandidateRepository
from app.repositories.watchlist import WatchlistRepository
from app.services.candidate_generation import CandidateGenerationService


LIFECYCLE_FILTERS = {
    "new": LifecycleStatus.NEW,
    "rising": LifecycleStatus.RISING,
    "stable": LifecycleStatus.STABLE,
    "declining": LifecycleStatus.DECLINING,
    "reviving": LifecycleStatus.REVIVING,
}

FORMAT_FILTERS = {
    "shorts": CreativeFormat.SHORT,
    "long": CreativeFormat.LONG,
    "both": CreativeFormat.BOTH,
}


class AdminCandidatesService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._candidates = DailyCandidateRepository(session)
        self._angles = CreativeAngleRepository(session)
        self._content = ContentRepository(session)
        self._watchlist = WatchlistRepository(session)
        self._generator = CandidateGenerationService(session)

    async def get_today_page(
        self,
        *,
        candidate_date: date | None = None,
        lifecycle: str | None = None,
        anime: str | None = None,
        format_filter: str | None = None,
        priority_only: bool = False,
    ) -> dict[str, Any]:
        candidate_date = candidate_date or datetime.now(UTC).date()
        rows = await self._candidates.list_for_date(candidate_date)
        if not rows:
            await self._generator.generate_for_date(candidate_date)
            rows = await self._candidates.list_for_date(candidate_date)

        priority_channels = await self._priority_channel_ids()
        grouped = await self._group_by_trend(rows, priority_channels)

        if lifecycle and lifecycle in LIFECYCLE_FILTERS:
            status = LIFECYCLE_FILTERS[lifecycle]
            grouped = [g for g in grouped if g["trend"].lifecycle_status == status]

        if anime:
            needle = anime.lower()
            grouped = [
                g
                for g in grouped
                if needle in (g["trend"].anime_title or "").lower()
                or needle in g["trend"].canonical_name.lower()
            ]

        if format_filter and format_filter in FORMAT_FILTERS:
            fmt = FORMAT_FILTERS[format_filter]
            for group in grouped:
                group["candidates"] = [c for c in group["candidates"] if c["angle"].format == fmt]
            grouped = [g for g in grouped if g["candidates"]]

        if priority_only:
            grouped = [g for g in grouped if g.get("has_priority_evidence")]

        total_angles = sum(len(g["candidates"]) for g in grouped)
        return {
            "date": candidate_date,
            "trend_groups": grouped,
            "total_count": total_angles,
            "selected_count": sum(
                1 for g in grouped for c in g["candidates"] if c["daily"].selected
            ),
        }

    async def _group_by_trend(
        self,
        rows: list[DailyCandidate],
        priority_channels: set[str],
    ) -> list[dict[str, Any]]:
        by_trend: dict[uuid.UUID, dict[str, Any]] = {}
        all_evidence_ids: list[uuid.UUID] = []

        for row in rows:
            angle = row.creative_angle
            trend = row.trend
            if angle is None or trend is None:
                continue
            for raw_id in angle.evidence_content_ids or []:
                try:
                    all_evidence_ids.append(uuid.UUID(str(raw_id)))
                except ValueError:
                    continue

        content_by_id = await self._content.get_by_ids(list(set(all_evidence_ids)))

        for row in rows:
            angle = row.creative_angle
            trend = row.trend
            if angle is None or trend is None:
                continue

            evidence_videos = []
            has_priority = False
            for raw_id in angle.evidence_content_ids or []:
                try:
                    cid = uuid.UUID(str(raw_id))
                except ValueError:
                    continue
                item = content_by_id.get(cid)
                if item is None:
                    continue
                if item.channel_external_id in priority_channels:
                    has_priority = True
                evidence_videos.append(item)

            bucket = by_trend.setdefault(
                trend.id,
                {
                    "trend": trend,
                    "candidates": [],
                    "has_priority_evidence": False,
                    "score_components": trend.score_components or {},
                },
            )
            bucket["has_priority_evidence"] = bucket["has_priority_evidence"] or has_priority
            bucket["candidates"].append(
                {
                    "daily": row,
                    "angle": angle,
                    "evidence_videos": evidence_videos[:3],
                    "has_priority_evidence": has_priority,
                },
            )

        groups = list(by_trend.values())
        groups.sort(key=lambda g: g["trend"].score or 0, reverse=True)
        return groups

    async def _priority_channel_ids(self) -> set[str]:
        items = await self._watchlist.list_items(tier=WatchTier.PRIORITY, enabled_only=True)
        return {str(i.external_id) for i in items if i.external_id}

    async def toggle_selection(self, daily_id: uuid.UUID) -> DailyCandidate | None:
        row = await self._session.get(DailyCandidate, daily_id)
        if row is None:
            return None
        row.selected = not row.selected
        angle = await self._angles.get_by_id(row.creative_angle_id)
        if angle is not None:
            from app.services.angle_status import AngleStatusService

            status_svc = AngleStatusService(self._session)
            target = AngleStatus.SELECTED if row.selected else AngleStatus.CANDIDATE
            if status_svc.can_transition(angle.status, target):
                await status_svc.transition(angle, target)
        await self._session.commit()
        return row

    async def update_note(self, angle_id: uuid.UUID, note: str) -> None:
        await self._angles.update_note(angle_id, note.strip() or None)
        await self._session.commit()

    async def build_fallback_from_angles(self, candidate_date: date) -> list[DailyCandidate]:
        angles = await self._angles.list_for_date(candidate_date)
        if not angles:
            return []
        stmt = select(TrendTheme).where(TrendTheme.id.in_([a.trend_id for a in angles]))
        trends = {t.id: t for t in (await self._session.scalars(stmt)).all()}
        rows: list[DailyCandidate] = []
        for rank, angle in enumerate(angles, start=1):
            trend = trends.get(angle.trend_id)
            row = DailyCandidate(
                date=candidate_date,
                creative_angle_id=angle.id,
                trend_id=angle.trend_id,
                rank=rank,
                candidate_score=trend.score if trend else None,
                score_snapshot=trend.score_components if trend else None,
                selected=angle.status == AngleStatus.SELECTED,
            )
            row.creative_angle = angle
            row.trend = trend
            rows.append(row)
        return rows
