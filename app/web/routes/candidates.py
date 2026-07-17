"""Today's candidates admin page."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import AngleStatus
from app.repositories.creative_angles import CreativeAngleRepository
from app.repositories.daily_candidates import DailyCandidateRepository
from app.services.admin_candidates import AdminCandidatesService
from app.services.angle_status import (
    AngleStatusService,
    InvalidStatusTransition,
    PublishedUrlChangeConflict,
    PublishedUrlConflict,
    PublishedUrlRequired,
)
from app.web.deps import TEMPLATES, flash_redirect, verify_csrf
from app.web.session import get_csrf_token

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.get("", response_class=HTMLResponse)
async def candidates_page(
    request: Request,
    d: str | None = None,
    lifecycle: str | None = None,
    anime: str | None = None,
    format: str | None = None,
    priority: str | None = None,
    flash: str | None = None,
    flash_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    candidate_date = date.fromisoformat(d) if d else None
    service = AdminCandidatesService(db)
    page = await service.get_today_page(
        candidate_date=candidate_date,
        lifecycle=lifecycle,
        anime=anime,
        format_filter=format,
        priority_only=priority == "1",
    )
    return TEMPLATES.TemplateResponse(
        request,
        "candidates/list.html",
        {
            **page,
            "lifecycle": lifecycle,
            "anime_filter": anime,
            "format_filter": format,
            "priority_filter": priority,
            "active_nav": "candidates",
            "flash_message": flash,
            "flash_type": flash_type,
            "csrf_token": get_csrf_token(request),
        },
    )


@router.post("/{daily_id}/toggle")
async def toggle_candidate(
    request: Request,
    daily_id: uuid.UUID,
    csrf_token: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    verify_csrf(request, form_token=csrf_token)
    service = AdminCandidatesService(db)
    row = await service.toggle_selection(daily_id)
    if row is None:
        return flash_redirect("/candidates", "候选不存在", error=True)
    state = "已入选" if row.selected else "已取消入选"
    return flash_redirect(f"/candidates?d={row.date.isoformat()}", state)


@router.post("/angles/{angle_id}/note")
async def update_angle_note(
    request: Request,
    angle_id: uuid.UUID,
    note: str = Form(""),
    candidate_date: str = Form(""),
    csrf_token: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    verify_csrf(request, form_token=csrf_token)
    service = AdminCandidatesService(db)
    await service.update_note(angle_id, note)
    url = f"/candidates?d={candidate_date}" if candidate_date else "/candidates"
    return flash_redirect(url, "备注已保存")


@router.post("/angles/{angle_id}/status")
async def update_angle_status(
    request: Request,
    angle_id: uuid.UUID,
    status: str = Form(...),
    note: str = Form(""),
    published_url: str = Form(""),
    candidate_date: str = Form(""),
    csrf_token: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    verify_csrf(request, form_token=csrf_token)
    angles = CreativeAngleRepository(db)
    angle = await angles.get_by_id(angle_id)
    if angle is None:
        return flash_redirect("/candidates", "方向不存在", error=True)

    try:
        target = AngleStatus(status)
    except ValueError:
        return flash_redirect("/candidates", "无效状态", error=True)

    url = f"/candidates?d={candidate_date}" if candidate_date else "/candidates"

    daily_candidate_id = None
    if candidate_date:
        daily = await DailyCandidateRepository(db).get_by_angle_and_date(
            angle_id, date.fromisoformat(candidate_date)
        )
        daily_candidate_id = daily.id if daily else None

    status_svc = AngleStatusService(db)
    try:
        await status_svc.transition(
            angle,
            target,
            note=note.strip() or None,
            published_url=published_url.strip() or None,
            daily_candidate_id=daily_candidate_id,
        )
        await db.commit()
    except InvalidStatusTransition as exc:
        return flash_redirect(url, str(exc), error=True)
    except PublishedUrlRequired:
        return flash_redirect(
            url,
            "标记发布需要有效的 YouTube 链接（watch / shorts / youtu.be）",
            error=True,
        )
    except PublishedUrlConflict:
        return flash_redirect(url, "该 YouTube 视频已绑定到其他创作方向", error=True)
    except PublishedUrlChangeConflict:
        return flash_redirect(url, "该方向已发布，不能更换为另一个 YouTube 视频", error=True)

    return flash_redirect(url, f"状态已更新为 {target.value}")
