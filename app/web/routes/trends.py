"""Trend detail admin page."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import ClusterDecisionAction, ClusterDecisionAudit, TrendTheme
from app.services.admin_trends import AdminTrendsService
from app.services.trend_consistency import TrendConsistencyService
from app.web.deps import TEMPLATES, flash_redirect, verify_csrf
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

    review_queue = list(
        (
            await db.scalars(
                select(ClusterDecisionAudit)
                .where(
                    ClusterDecisionAudit.action == ClusterDecisionAction.NEEDS_REVIEW,
                    ClusterDecisionAudit.rolled_back.is_(False),
                )
                .order_by(ClusterDecisionAudit.created_at.desc())
                .limit(20),
            )
        ).all(),
    )
    other_trends = list(
        (
            await db.scalars(
                select(TrendTheme)
                .where(TrendTheme.id != trend_id)
                .order_by(TrendTheme.last_active_at.desc())
                .limit(50),
            )
        ).all(),
    )

    return TEMPLATES.TemplateResponse(
        request,
        "trends/detail.html",
        {
            **detail,
            "review_queue": review_queue,
            "other_trends": other_trends,
            "active_nav": "candidates",
            "csrf_token": get_csrf_token(request),
        },
    )


@router.post("/{trend_id}/merge")
async def merge_trend(
    request: Request,
    trend_id: uuid.UUID,
    target_trend_id: str = Form(...),
    note: str = Form(""),
    csrf_token: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    verify_csrf(request, form_token=csrf_token)
    try:
        target_id = uuid.UUID(target_trend_id)
        svc = TrendConsistencyService(db)
        await svc.manual_merge(
            source_trend_id=trend_id,
            target_trend_id=target_id,
            note=note.strip() or None,
        )
        await db.commit()
    except (ValueError, Exception) as exc:  # noqa: BLE001
        return flash_redirect(f"/trends/{trend_id}", str(exc), error=True)
    return flash_redirect(f"/trends/{target_id}", "已合并到目标趋势")


@router.post("/{trend_id}/members/{content_item_id}/move-out")
async def move_member_out(
    request: Request,
    trend_id: uuid.UUID,
    content_item_id: uuid.UUID,
    note: str = Form(""),
    csrf_token: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    verify_csrf(request, form_token=csrf_token)
    try:
        svc = TrendConsistencyService(db)
        await svc.manual_move_out(
            trend_id=trend_id,
            content_item_id=content_item_id,
            note=note.strip() or None,
        )
        await db.commit()
    except ValueError as exc:
        return flash_redirect(f"/trends/{trend_id}", str(exc), error=True)
    return flash_redirect(f"/trends/{trend_id}", "成员已移出当前趋势")
