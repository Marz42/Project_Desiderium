"""Trend detail admin page."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.services.admin_trends import AdminTrendsService
from app.web.deps import TEMPLATES, flash_redirect
from app.web.session import get_csrf_token

router = APIRouter(prefix="/trends", tags=["trends"])


@router.get("/{trend_id}", response_class=HTMLResponse)
async def trend_detail(
    request: Request,
    trend_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    service = AdminTrendsService(db)
    detail = await service.get_detail(trend_id)
    if detail is None:
        return flash_redirect("/candidates", "趋势不存在", error=True)

    return TEMPLATES.TemplateResponse(
        request,
        "trends/detail.html",
        {
            **detail,
            "active_nav": "candidates",
            "csrf_token": get_csrf_token(request),
        },
    )
