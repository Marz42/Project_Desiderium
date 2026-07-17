"""Markdown and HTML brief export.

GET reads are side-effect-free: previewing a brief never auto-syncs from the
day's selection and never marks it exported. Syncing and finalizing are
explicit POST actions (see app/web/routes/brief.py). Export prefers a
finalized content snapshot when one exists, so downloads stay stable even if
the underlying angles/trends change later.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Brief, CreativeFormat, LifecycleStatus
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
        """Read-only: renders the brief's current draft items. Never syncs."""
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
            assert trend_section is not None
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
        sections = await self._resolve_export_sections(brief_date)
        template = self._env.get_template("brief.md.j2")
        return template.render(
            brief_date=brief_date,
            sections=sections,
            lifecycle_labels=LIFECYCLE_LABELS,
            format_labels=FORMAT_LABELS,
        )

    async def render_html(self, brief_date: date) -> str:
        sections = await self._resolve_export_sections(brief_date)
        template = self._env.get_template("brief.html.j2")
        return template.render(
            brief_date=brief_date,
            sections=sections,
            lifecycle_labels=LIFECYCLE_LABELS,
            format_labels=FORMAT_LABELS,
        )

    async def _resolve_export_sections(self, brief_date: date) -> list[Any]:
        """Finalized snapshot when present; otherwise the current draft."""
        brief = await self._briefs.get_or_create(brief_date)
        if brief.finalized_snapshot:
            return _deserialize_sections(brief.finalized_snapshot)
        data = await self.get_preview_data(brief_date)
        return data["sections"]

    async def finalize_brief(
        self,
        brief_date: date,
        *,
        finalized_by: str = "admin",
    ) -> Brief | None:
        """Freeze the current draft into an immutable content snapshot.

        Requires an explicit prior sync; does not sync implicitly. Returns
        None if there is nothing to finalize (no synced items yet).
        """
        data = await self.get_preview_data(brief_date)
        brief = data["brief"]
        if brief.finalized_snapshot is not None:
            return brief
        sections = data["sections"]
        if not sections:
            return None
        serialized = _serialize_sections(sections)
        content_hash = hashlib.sha256(
            json.dumps(serialized, sort_keys=True, ensure_ascii=False).encode("utf-8"),
        ).hexdigest()
        finalized = await self._briefs.finalize(
            brief.id,
            serialized,
            content_hash,
            finalized_by=finalized_by,
        )
        await self._session.commit()
        return finalized

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


def _serialize_sections(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert live ORM-backed preview sections into JSON-safe frozen data."""
    serialized: list[dict[str, Any]] = []
    for section in sections:
        trend = section["trend"]
        serialized.append(
            {
                "trend": {
                    "canonical_name": trend.canonical_name,
                    "lifecycle_status": trend.lifecycle_status.value,
                    "score": trend.score,
                    "score_components": trend.score_components,
                    "summary_zh": trend.summary_zh,
                },
                "why_trending": section.get("why_trending"),
                "evidence_videos": [
                    {
                        "title_original": v.title_original,
                        "title_zh": v.title_zh,
                        "channel_name": v.channel_name,
                        "published_at": v.published_at.isoformat() if v.published_at else None,
                        "url": v.url,
                    }
                    for v in section["evidence_videos"]
                ],
                "angles": [
                    {
                        "angle_zh": row["angle"].angle_zh,
                        "format": row["angle"].format.value,
                        "manager_note": row["manager_note"],
                    }
                    for row in section["angles"]
                ],
            },
        )
    return serialized


def _deserialize_sections(snapshot: list[dict[str, Any]]) -> list[SimpleNamespace]:
    """Rehydrate a frozen snapshot into template-compatible namespaces."""
    sections: list[SimpleNamespace] = []
    for section in snapshot:
        trend = section["trend"]
        trend_ns = SimpleNamespace(
            canonical_name=trend["canonical_name"],
            lifecycle_status=LifecycleStatus(trend["lifecycle_status"]),
            score=trend["score"],
            score_components=trend["score_components"],
            summary_zh=trend["summary_zh"],
        )
        videos_ns = [
            SimpleNamespace(
                title_original=v["title_original"],
                title_zh=v["title_zh"],
                channel_name=v["channel_name"],
                published_at=(
                    datetime.fromisoformat(v["published_at"]) if v["published_at"] else None
                ),
                url=v["url"],
            )
            for v in section["evidence_videos"]
        ]
        angles_ns = [
            SimpleNamespace(
                angle=SimpleNamespace(
                    angle_zh=a["angle_zh"],
                    format=CreativeFormat(a["format"]),
                ),
                manager_note=a["manager_note"],
            )
            for a in section["angles"]
        ]
        sections.append(
            SimpleNamespace(
                trend=trend_ns,
                why_trending=section.get("why_trending"),
                evidence_videos=videos_ns,
                angles=angles_ns,
            ),
        )
    return sections
