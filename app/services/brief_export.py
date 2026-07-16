"""Markdown and HTML brief export."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CreativeFormat
from app.repositories.briefs import BriefRepository
from app.repositories.content import ContentRepository
from app.repositories.daily_candidates import DailyCandidateRepository
from app.services.admin_candidates import AdminCandidatesService

TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "web" / "templates" / "export"

LIFECYCLE_LABELS = {
    "new": "新发现",
    "rising": "持续上升",
    "stable": "热度稳定",
    "declining": "开始下降",
    "reviving": "重新升温",
    "dormant": "休眠",
}

FORMAT_LABELS = {
    CreativeFormat.SHORT: "Shorts",
    CreativeFormat.LONG: "长视频",
    CreativeFormat.BOTH: "Both",
}


class BriefExportService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._briefs = BriefRepository(session)
        self._candidates = DailyCandidateRepository(session)
        self._content = ContentRepository(session)
        self._admin = AdminCandidatesService(session)
        self._env = Environment(
            loader=FileSystemLoader(str(TEMPLATE_DIR)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    async def sync_brief_from_selection(self, brief_date: date) -> None:
        rows = await self._candidates.list_for_date(brief_date)
        selected = [r for r in rows if r.selected]
        if not selected:
            page = await self._admin.get_today_page(candidate_date=brief_date)
            angle_ids = []
            notes: dict = {}
            position = 1
            for group in page["trend_groups"]:
                for cand in group["candidates"]:
                    if not cand["daily"].selected:
                        continue
                    angle = cand["angle"]
                    angle_ids.append(angle.id)
                    notes[angle.id] = angle.manager_note
                    position += 1
            if not angle_ids:
                return
            brief = await self._briefs.get_or_create(brief_date)
            await self._briefs.replace_items(brief.id, angle_ids, notes=notes)
            await self._session.commit()
            return

        selected.sort(key=lambda r: r.rank)
        brief = await self._briefs.get_or_create(brief_date)
        angle_ids = [r.creative_angle_id for r in selected]
        notes = {
            r.creative_angle_id: (r.creative_angle.manager_note if r.creative_angle else None)
            for r in selected
        }
        await self._briefs.replace_items(brief.id, angle_ids, notes=notes)
        await self._session.commit()

    async def get_preview_data(self, brief_date: date) -> dict[str, Any]:
        await self.sync_brief_from_selection(brief_date)
        brief = await self._briefs.get_or_create(brief_date)
        sections: list[dict[str, Any]] = []
        current_trend_id = None
        trend_section: dict[str, Any] | None = None

        for item in sorted(brief.items, key=lambda i: i.position):
            angle = item.creative_angle
            trend = angle.trend if angle else None
            if trend is None or angle is None:
                continue

            if trend.id != current_trend_id:
                if trend_section is not None:
                    sections.append(trend_section)
                current_trend_id = trend.id
                evidence_ids = []
                for raw in angle.evidence_content_ids or []:
                    try:
                        import uuid

                        evidence_ids.append(uuid.UUID(str(raw)))
                    except ValueError:
                        continue
                videos = list((await self._content.get_by_ids(evidence_ids)).values())
                trend_section = {
                    "trend": trend,
                    "angles": [],
                    "evidence_videos": videos[:5],
                    "why_trending": trend.summary_zh,
                }
            trend_section["angles"].append(
                {
                    "item": item,
                    "angle": angle,
                    "manager_note": item.manager_note or angle.manager_note,
                },
            )

        if trend_section is not None:
            sections.append(trend_section)

        return {"brief": brief, "brief_date": brief_date, "sections": sections}

    async def render_markdown(self, brief_date: date) -> str:
        data = await self.get_preview_data(brief_date)
        template = self._env.get_template("brief.md.j2")
        return template.render(
            brief_date=brief_date,
            sections=data["sections"],
            lifecycle_labels=LIFECYCLE_LABELS,
            format_labels=FORMAT_LABELS,
        )

    async def render_html(self, brief_date: date) -> str:
        data = await self.get_preview_data(brief_date)
        template = self._env.get_template("brief.html.j2")
        return template.render(
            brief_date=brief_date,
            sections=data["sections"],
            lifecycle_labels=LIFECYCLE_LABELS,
            format_labels=FORMAT_LABELS,
        )

    async def reorder_items(self, brief_date: date, ordered_item_ids: list) -> None:
        import uuid

        brief = await self._briefs.get_or_create(brief_date)
        ids = [uuid.UUID(str(i)) for i in ordered_item_ids]
        await self._briefs.reorder_items(brief.id, ids)
        await self._session.commit()

    async def update_item_note(self, item_id, note: str) -> None:
        import uuid

        await self._briefs.update_item_note(uuid.UUID(str(item_id)), note.strip() or None)
        await self._session.commit()

    async def mark_exported(self, brief_date: date) -> None:
        brief = await self._briefs.get_or_create(brief_date)
        await self._briefs.mark_exported(brief.id)
        await self._session.commit()
