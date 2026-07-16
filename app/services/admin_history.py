"""Admin history page data."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AngleStatus
from app.repositories.creative_angles import CreativeAngleRepository
from app.repositories.daily_candidates import DailyCandidateRepository


STATUS_FILTERS = {
    "selected": "selected",
    "published": AngleStatus.PUBLISHED.value,
    "reusable": AngleStatus.REUSABLE.value,
    "blocked": AngleStatus.BLOCKED.value,
    "adopted": AngleStatus.ADOPTED.value,
}


class AdminHistoryService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._candidates = DailyCandidateRepository(session)
        self._angles = CreativeAngleRepository(session)

    async def list_available_dates(self) -> list[date]:
        return await self._candidates.list_dates()

    async def get_history_page(
        self,
        *,
        history_date: date,
        status_filter: str | None = None,
    ) -> dict[str, Any]:
        rows = await self._candidates.list_for_date(history_date)
        entries: list[dict[str, Any]] = []

        for row in rows:
            angle = row.creative_angle
            trend = row.trend
            if angle is None:
                continue

            pub_records = angle.publication_records or []
            latest_pub = pub_records[-1] if pub_records else None

            entry = {
                "daily": row,
                "angle": angle,
                "trend": trend,
                "publication": latest_pub,
            }
            entries.append(entry)

        if status_filter == "selected":
            entries = [e for e in entries if e["daily"].selected]
        elif status_filter in STATUS_FILTERS and status_filter != "selected":
            target = AngleStatus(STATUS_FILTERS[status_filter])
            entries = [e for e in entries if e["angle"].status == target]

        return {
            "date": history_date,
            "entries": entries,
            "status_filter": status_filter,
            "available_dates": await self.list_available_dates(),
        }
