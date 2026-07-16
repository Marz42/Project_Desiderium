"""Isolated TikTok ingestion service — failures do not affect YouTube."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.tiktok import CookieExpiredError, TikTokAdapter, TikTokClient, get_tiktok_config
from app.config import Settings, get_settings
from app.models import (
    CrawlJob,
    CrawlJobAdapter,
    CrawlJobStatus,
    CrawlJobType,
    Platform,
    WatchItem,
    WatchItemType,
    WatchTier,
)
from app.repositories.content import ContentRepository
from app.repositories.watchlist import CrawlJobRepository, WatchlistRepository
from app.schemas.watchlist import watch_item_for_adapter

logger = logging.getLogger(__name__)


class TikTokIngestionService:
    def __init__(
        self,
        session: AsyncSession,
        adapter: TikTokAdapter,
        settings: Settings | None = None,
    ) -> None:
        self._session = session
        self._adapter = adapter
        self._settings = settings or get_settings()
        self._watchlist = WatchlistRepository(session)
        self._content = ContentRepository(session)
        self._jobs = CrawlJobRepository(session)

    async def crawl_watch_item(self, watch_item_id: uuid.UUID) -> CrawlJob:
        item = await self._watchlist.get_by_id(watch_item_id)
        if item is None:
            raise ValueError("watch item not found")
        if not item.enabled:
            raise ValueError("watch item is disabled")
        if item.platform != Platform.TIKTOK:
            raise ValueError("not a TikTok watch item")

        job = await self._jobs.create(
            adapter=CrawlJobAdapter.TIKTOK,
            job_type=CrawlJobType.DISCOVER,
            watch_item_id=item.id,
        )
        await self._jobs.start(job)

        try:
            result = await self._run_crawl(item)
            status = CrawlJobStatus.SUCCESS
            if result.get("partial"):
                status = CrawlJobStatus.PARTIAL
            if result.get("cookie_expired"):
                status = CrawlJobStatus.FAILED
            await self._jobs.finish(
                job,
                status=status,
                items_processed=result.get("items_processed", 0),
                error_code=result.get("error_code"),
                error_message=result.get("error_message"),
            )
            await self._session.commit()
            return job
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "TikTok crawl failed for watch item %s",
                watch_item_id,
                extra={"service": "tiktok", "component": "ingestion", "alert": True},
            )
            await self._watchlist.update_crawl_status(item, success=False)
            await self._jobs.finish(
                job,
                status=CrawlJobStatus.FAILED,
                error_code=type(exc).__name__,
                error_message=str(exc)[:500],
            )
            await self._session.commit()
            return job

    async def _run_crawl(self, item: WatchItem) -> dict[str, Any]:
        watch_dict = watch_item_for_adapter(item, [])
        cursor = (item.config or {}).get("page_token")
        discover = await self._adapter.discover_items(watch_dict, cursor=cursor)

        if discover.get("cookie_expired"):
            await self._watchlist.update_crawl_status(
                item,
                success=False,
                config_patch={"cookie_expired": True},
            )
            return {
                "items_processed": 0,
                "partial": False,
                "cookie_expired": True,
                "error_code": "CookieExpired",
                "error_message": discover.get("error"),
            }

        raw_videos = discover.get("raw_videos") or []
        if raw_videos:
            self._adapter.cache_discovered_videos(raw_videos)

        candidate_ids = discover.get("external_ids") or []
        known = await self._content.get_known_external_ids(Platform.TIKTOK, candidate_ids)
        external_ids = [vid for vid in candidate_ids if vid not in known]
        items_processed = 0
        partial = bool(discover.get("error"))

        video_by_id = {str(v.get("id", "")): v for v in raw_videos}
        for ext_id in external_ids:
            raw = video_by_id.get(ext_id)
            if not raw:
                continue
            normalized = self._adapter.normalize_item(raw)
            _, is_new = await self._content.upsert_content(
                platform=Platform.TIKTOK,
                normalized=normalized,
                source_watch_item_id=item.id,
            )
            if is_new:
                items_processed += 1

        config_patch: dict[str, Any] = {}
        if discover.get("next_cursor"):
            config_patch["page_token"] = discover["next_cursor"]

        await self._watchlist.update_crawl_status(
            item,
            success=not partial,
            partial=partial,
            config_patch=config_patch,
        )

        return {
            "items_processed": items_processed,
            "partial": partial,
            "error_code": "PartialError" if partial else None,
            "error_message": discover.get("error"),
        }

    async def crawl_batch(
        self,
        *,
        tier: WatchTier | None = None,
        item_types: set[WatchItemType] | None = None,
    ) -> dict[str, Any]:
        items = await self._watchlist.list_items(
            tier=tier,
            enabled_only=True,
            platform=Platform.TIKTOK,
        )
        if item_types:
            items = [i for i in items if i.type in item_types]

        summary = {
            "platform": "tiktok",
            "tier": tier.value if tier else "all",
            "total": len(items),
            "succeeded": 0,
            "failed": 0,
            "new_items": 0,
            "errors": [],
        }

        for item in items:
            if self._adapter.cookie_expired:
                summary["errors"].append("skipped remaining items: cookie expired")
                break
            try:
                job = await self.crawl_watch_item(item.id)
                if job.status in {CrawlJobStatus.SUCCESS, CrawlJobStatus.PARTIAL}:
                    summary["succeeded"] += 1
                    summary["new_items"] += job.items_processed
                else:
                    summary["failed"] += 1
                    if job.error_message:
                        summary["errors"].append(f"{item.name}: {job.error_message}")
            except CookieExpiredError as exc:
                summary["failed"] += 1
                summary["errors"].append(f"cookie expired at {item.name}: {exc}")
                break
            except Exception as exc:  # noqa: BLE001
                summary["failed"] += 1
                summary["errors"].append(f"{item.name}: {exc}")
                logger.exception(
                    "TikTok batch crawl item failed: %s",
                    item.name,
                    extra={"service": "tiktok", "component": "ingestion"},
                )

        return summary


async def create_tiktok_ingestion(session: AsyncSession) -> tuple[TikTokIngestionService, TikTokAdapter]:
    settings = get_settings()
    if not settings.tiktok_enabled:
        raise RuntimeError("TikTok adapter is disabled")

    tiktok_yaml = get_tiktok_config()
    client = TikTokClient(
        settings.tiktok_cookie,
        page_version=str(tiktok_yaml.get("page_version", settings.tiktok_page_version)),
        user_agent=tiktok_yaml.get("user_agent"),
    )
    adapter = TikTokAdapter(
        client,
        enabled=settings.tiktok_enabled,
        page_version=str(tiktok_yaml.get("page_version", settings.tiktok_page_version)),
    )
    return TikTokIngestionService(session, adapter, settings), adapter
