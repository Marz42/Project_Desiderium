from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.templating import Jinja2Templates

from app.db import get_db
from app.jobs.crawl_tasks import crawl_single_item
from app.models import Platform, WatchItemType, WatchTier
from app.repositories.watchlist import CrawlJobRepository
from app.schemas.watchlist import WatchItemCreate, WatchItemUpdate, parse_tags
from app.services.watchlist import WatchlistService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/watchlist", tags=["watchlist"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

TIERS = [t.value for t in WatchTier]
TYPES = [t.value for t in WatchItemType]
PLATFORMS = [p.value for p in Platform]


def _flash_redirect(url: str, message: str, *, error: bool = False) -> RedirectResponse:
    sep = "&" if "?" in url else "?"
    flash_type = "error" if error else "success"
    return RedirectResponse(f"{url}{sep}flash={message}&flash_type={flash_type}", status_code=303)


@router.get("", response_class=HTMLResponse)
async def list_watchlist(
    request: Request,
    tier: str | None = None,
    enabled: str | None = None,
    flash: str | None = None,
    flash_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    service = WatchlistService(db)
    filter_tier = WatchTier(tier) if tier in TIERS else None
    enabled_only = enabled == "true"
    items = await service.list_items(tier=filter_tier, enabled_only=enabled_only)

    if enabled == "false":
        items = [i for i in items if not i["enabled"]]

    return templates.TemplateResponse(
        request,
        "watchlist/list.html",
        {
            "items": items,
            "tiers": TIERS,
            "filter_tier": tier,
            "filter_enabled": enabled,
            "active_nav": "watchlist",
            "flash_message": flash,
            "flash_type": flash_type,
        },
    )


@router.get("/new", response_class=HTMLResponse)
async def new_watchlist_form(request: Request):
    return templates.TemplateResponse(
        request,
        "watchlist/form.html",
        {"item": None, "tiers": TIERS, "types": TYPES, "platforms": PLATFORMS, "active_nav": "watchlist"},
    )


@router.post("")
async def create_watchlist(
    type: str = Form(...),
    platform: str = Form(...),
    name: str = Form(...),
    url_or_id: str = Form(""),
    tier: str = Form("general"),
    tags: str = Form(""),
    note: str = Form(""),
    enabled: str = Form("true"),
    db: AsyncSession = Depends(get_db),
):
    service = WatchlistService(db)
    external_id = url_or_id.strip() or name.strip()
    if type in {"keyword", "anime"}:
        external_id = " ".join(external_id.lower().split())

    try:
        await service.create_item(
            WatchItemCreate(
                type=WatchItemType(type),
                platform=Platform(platform),
                name=name.strip(),
                external_id=external_id,
                url=url_or_id.strip() or None,
                tier=WatchTier(tier),
                tags=parse_tags(tags),
                note=note.strip() or None,
                enabled=enabled.lower() in {"true", "1", "yes"},
            )
        )
    except Exception as exc:  # noqa: BLE001
        return _flash_redirect("/watchlist/new", str(exc), error=True)

    return _flash_redirect("/watchlist", f"已创建监控项：{name}")


@router.get("/import", response_class=HTMLResponse)
async def import_form(request: Request, flash: str | None = None, flash_type: str | None = None):
    return templates.TemplateResponse(
        request,
        "watchlist/import.html",
        {
            "result": None,
            "active_nav": "watchlist",
            "flash_message": flash,
            "flash_type": flash_type,
        },
    )


@router.post("/import", response_class=HTMLResponse)
async def import_csv(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    content = (await file.read()).decode("utf-8-sig")
    service = WatchlistService(db)
    result = await service.import_csv(content)
    return templates.TemplateResponse(
        request,
        "watchlist/import.html",
        {"result": result, "active_nav": "watchlist"},
    )


@router.get("/{item_id}", response_class=HTMLResponse)
async def watchlist_detail(
    request: Request,
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    service = WatchlistService(db)
    item = await service.get_item(item_id)
    if item is None:
        return _flash_redirect("/watchlist", "监控项不存在", error=True)

    jobs_repo = CrawlJobRepository(db)
    jobs = await jobs_repo.list_recent_for_item(item_id)
    crawl_jobs = [
        {
            "status": j.status.value,
            "started_at": j.started_at,
            "created_at": j.created_at,
            "items_processed": j.items_processed,
            "error_message": j.error_message,
        }
        for j in jobs
    ]

    return templates.TemplateResponse(
        request,
        "watchlist/detail.html",
        {"item": item, "crawl_jobs": crawl_jobs, "active_nav": "watchlist"},
    )


@router.get("/{item_id}/edit", response_class=HTMLResponse)
async def edit_watchlist_form(
    request: Request,
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    service = WatchlistService(db)
    item = await service.get_item(item_id)
    if item is None:
        return _flash_redirect("/watchlist", "监控项不存在", error=True)

    return templates.TemplateResponse(
        request,
        "watchlist/form.html",
        {"item": item, "tiers": TIERS, "types": TYPES, "platforms": PLATFORMS, "active_nav": "watchlist"},
    )


@router.post("/{item_id}")
async def update_watchlist(
    item_id: uuid.UUID,
    name: str = Form(...),
    url_or_id: str = Form(""),
    tier: str = Form("general"),
    tags: str = Form(""),
    note: str = Form(""),
    enabled: str = Form("true"),
    db: AsyncSession = Depends(get_db),
):
    service = WatchlistService(db)
    try:
        await service.update_item(
            item_id,
            WatchItemUpdate(
                name=name.strip(),
                url=url_or_id.strip() or None,
                tier=WatchTier(tier),
                tags=parse_tags(tags),
                note=note.strip() or None,
                enabled=enabled.lower() in {"true", "1", "yes"},
            ),
        )
    except Exception as exc:  # noqa: BLE001
        return _flash_redirect(f"/watchlist/{item_id}/edit", str(exc), error=True)

    return _flash_redirect(f"/watchlist/{item_id}", "已更新监控项")


@router.post("/{item_id}/toggle")
async def toggle_watchlist(item_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    service = WatchlistService(db)
    try:
        item = await service.toggle_enabled(item_id)
    except Exception as exc:  # noqa: BLE001
        return _flash_redirect("/watchlist", str(exc), error=True)
    state = "启用" if item["enabled"] else "停用"
    return _flash_redirect("/watchlist", f"已{state}：{item['name']}")


@router.post("/{item_id}/crawl")
async def trigger_crawl(item_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    service = WatchlistService(db)
    item = await service.get_item(item_id)
    if item is None:
        return _flash_redirect("/watchlist", "监控项不存在", error=True)

    try:
        result = await crawl_single_item(item_id)
        msg = f"抓取完成：{result['status']}，新增 {result['items_processed']} 项"
        if result.get("error_message"):
            msg += f" ({result['error_message']})"
    except Exception as exc:  # noqa: BLE001
        logger.exception("manual crawl failed")
        return _flash_redirect(f"/watchlist/{item_id}", str(exc), error=True)

    return _flash_redirect(f"/watchlist/{item_id}", msg)


@router.post("/{item_id}/delete")
async def delete_watchlist(item_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    service = WatchlistService(db)
    try:
        await service.delete_item(item_id)
    except Exception as exc:  # noqa: BLE001
        return _flash_redirect("/watchlist", str(exc), error=True)
    return _flash_redirect("/watchlist", "已删除监控项")
