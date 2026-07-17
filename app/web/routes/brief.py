"""Brief preview and export."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.services.brief_export import BriefExportService
from app.web.deps import TEMPLATES, flash_redirect, verify_csrf
from app.web.session import get_csrf_token

router = APIRouter(prefix="/brief", tags=["brief"])


@router.get("", response_class=HTMLResponse)
async def brief_preview(
    request: Request,
    d: str | None = None,
    flash: str | None = None,
    flash_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    brief_date = date.fromisoformat(d) if d else date.today()
    service = BriefExportService(db)
    data = await service.get_preview_data(brief_date)
    markdown_preview = await service.render_markdown(brief_date)

    return TEMPLATES.TemplateResponse(
        request,
        "brief/preview.html",
        {
            **data,
            "markdown_preview": markdown_preview,
            "active_nav": "brief",
            "flash_message": flash,
            "flash_type": flash_type,
            "csrf_token": get_csrf_token(request),
        },
    )


@router.post("/reorder")
async def reorder_brief(
    request: Request,
    brief_date: str = Form(...),
    item_ids: str = Form(...),
    csrf_token: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    verify_csrf(request, form_token=csrf_token)
    ordered = [part.strip() for part in item_ids.split(",") if part.strip()]
    service = BriefExportService(db)
    await service.reorder_items(date.fromisoformat(brief_date), ordered)
    return flash_redirect(f"/brief?d={brief_date}", "顺序已更新")


@router.post("/items/{item_id}/note")
async def update_brief_item_note(
    request: Request,
    item_id: uuid.UUID,
    note: str = Form(""),
    brief_date: str = Form(""),
    csrf_token: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    verify_csrf(request, form_token=csrf_token)
    service = BriefExportService(db)
    await service.update_item_note(item_id, note)
    url = f"/brief?d={brief_date}" if brief_date else "/brief"
    return flash_redirect(url, "简报备注已保存")


@router.post("/sync")
async def sync_brief(
    request: Request,
    brief_date: str = Form(...),
    csrf_token: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    verify_csrf(request, form_token=csrf_token)
    service = BriefExportService(db)
    await service.sync_brief_from_selection(date.fromisoformat(brief_date))
    return flash_redirect(f"/brief?d={brief_date}", "已从今日入选同步简报")


@router.post("/finalize")
async def finalize_brief(
    request: Request,
    brief_date: str = Form(...),
    csrf_token: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    verify_csrf(request, form_token=csrf_token)
    service = BriefExportService(db)
    finalized = await service.finalize_brief(
        date.fromisoformat(brief_date),
        finalized_by="admin",
    )
    if finalized is None:
        return flash_redirect(
            f"/brief?d={brief_date}", "没有可固化的内容，请先同步入选方向", error=True
        )
    return flash_redirect(f"/brief?d={brief_date}", "简报内容已固化，导出将使用固化快照")


@router.get("/export/markdown")
async def export_markdown(d: str | None = None, db: AsyncSession = Depends(get_db)):
    brief_date = date.fromisoformat(d) if d else date.today()
    service = BriefExportService(db)
    content = await service.render_markdown(brief_date)
    await service.mark_exported(brief_date)
    filename = f"brief-{brief_date.isoformat()}.md"
    return PlainTextResponse(
        content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/html")
async def export_html(d: str | None = None, db: AsyncSession = Depends(get_db)):
    brief_date = date.fromisoformat(d) if d else date.today()
    service = BriefExportService(db)
    content = await service.render_html(brief_date)
    await service.mark_exported(brief_date)
    filename = f"brief-{brief_date.isoformat()}.html"
    return Response(
        content,
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
