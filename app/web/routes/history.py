"""Historical candidates admin page."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.services.admin_history import AdminHistoryService
from app.web.deps import TEMPLATES
from app.web.session import get_csrf_token

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_class=HTMLResponse)
async def history_page(
    request: Request,
    d: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    service = AdminHistoryService(db)
    dates = await service.list_available_dates()
    history_date = date.fromisoformat(d) if d else (dates[0] if dates else date.today())
    page = await service.get_history_page(history_date=history_date, status_filter=status)

    return TEMPLATES.TemplateResponse(
        request,
        "history/list.html",
        {
            **page,
            "active_nav": "history",
            "csrf_token": get_csrf_token(request),
        },
    )
