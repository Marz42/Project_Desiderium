"""G4 admin analytics page: adoption/publish funnel + PerformanceRatio."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.services.performance_analytics import PerformanceAnalyticsService
from app.web.deps import TEMPLATES
from app.web.session import get_csrf_token

router = APIRouter(prefix="/performance", tags=["performance"])


@router.get("", response_class=HTMLResponse)
async def performance_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    service = PerformanceAnalyticsService(db)
    data = await service.get_overview()
    return TEMPLATES.TemplateResponse(
        request,
        "performance/list.html",
        {
            **data,
            "active_nav": "performance",
            "csrf_token": get_csrf_token(request),
        },
    )
