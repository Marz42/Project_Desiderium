"""Brief repository."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Brief, BriefItem, BriefStatus, CreativeAngle, TrendTheme


class BriefRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_date(self, brief_date: date) -> Brief | None:
        stmt = (
            select(Brief)
            .where(Brief.brief_date == brief_date)
            .options(
                selectinload(Brief.items).selectinload(BriefItem.creative_angle).selectinload(CreativeAngle.trend),
            )
        )
        return await self._session.scalar(stmt)

    async def get_or_create(self, brief_date: date) -> Brief:
        brief = await self.get_by_date(brief_date)
        if brief is not None:
            return brief
        brief = Brief(
            brief_date=brief_date,
            title=f"今日番剧解说趋势简报 — {brief_date.isoformat()}",
            status=BriefStatus.DRAFT,
        )
        self._session.add(brief)
        await self._session.flush()
        return brief

    async def replace_items(
        self,
        brief_id: uuid.UUID,
        angle_ids: list[uuid.UUID],
        *,
        notes: dict[uuid.UUID, str | None] | None = None,
    ) -> list[BriefItem]:
        await self._session.execute(delete(BriefItem).where(BriefItem.brief_id == brief_id))
        notes = notes or {}
        items: list[BriefItem] = []
        for position, angle_id in enumerate(angle_ids, start=1):
            item = BriefItem(
                brief_id=brief_id,
                creative_angle_id=angle_id,
                position=position,
                manager_note=notes.get(angle_id),
            )
            self._session.add(item)
            items.append(item)
        await self._session.flush()
        return items

    async def update_item_note(self, item_id: uuid.UUID, note: str | None) -> BriefItem | None:
        item = await self._session.get(BriefItem, item_id)
        if item is None:
            return None
        item.manager_note = note
        await self._session.flush()
        return item

    async def reorder_items(self, brief_id: uuid.UUID, ordered_item_ids: list[uuid.UUID]) -> None:
        stmt = select(BriefItem).where(BriefItem.brief_id == brief_id)
        items = {item.id: item for item in (await self._session.scalars(stmt)).all()}
        for position, item_id in enumerate(ordered_item_ids, start=1):
            item = items.get(item_id)
            if item is not None:
                item.position = position
        await self._session.flush()

    async def mark_exported(self, brief_id: uuid.UUID) -> None:
        brief = await self._session.get(Brief, brief_id)
        if brief is None:
            return
        from datetime import UTC, datetime

        brief.status = BriefStatus.EXPORTED
        brief.exported_at = datetime.now(UTC)
        await self._session.flush()

    async def load_export_data(self, brief_date: date) -> list[dict]:
        brief = await self.get_by_date(brief_date)
        if brief is None:
            return []

        rows: list[dict] = []
        for item in sorted(brief.items, key=lambda i: i.position):
            angle = item.creative_angle
            if angle is None:
                continue
            trend: TrendTheme | None = angle.trend
            rows.append(
                {
                    "position": item.position,
                    "angle": angle,
                    "trend": trend,
                    "manager_note": item.manager_note or angle.manager_note,
                },
            )
        return rows
