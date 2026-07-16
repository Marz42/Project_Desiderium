from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.youtube import QuotaExceededError, YouTubeAdapter, YouTubeClient
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


class IngestionService:
    def __init__(
        self,
        session: AsyncSession,
        adapter: YouTubeAdapter,
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

        job = await self._jobs.create(
            adapter=CrawlJobAdapter.YOUTUBE,
            job_type=CrawlJobType.DISCOVER,
            watch_item_id=item.id,
        )
        await self._jobs.start(job)

        try:
            result = await self._run_crawl(item)
            status = CrawlJobStatus.SUCCESS
            if result.get("partial"):
                status = CrawlJobStatus.PARTIAL
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
            logger.exception("crawl failed for watch item %s", watch_item_id)
            await self._watchlist.update_crawl_status(item, success=False)
            await self._jobs.finish(
                job,
                status=CrawlJobStatus.FAILED,
                error_code=type(exc).__name__,
                error_message=str(exc)[:500],
            )
            await self._session.commit()
            raise

    async def _run_crawl(self, item: WatchItem) -> dict[str, Any]:
        watch_dict = watch_item_for_adapter(item, [])
        cursor = (item.config or {}).get("page_token")
        discover = await self._adapter.discover_items(watch_dict, cursor=cursor)

        if discover.get("quota_exhausted"):
            await self._watchlist.update_crawl_status(
                item,
                success=False,
                config_patch={"quota_exhausted": True},
            )
            return {
                "items_processed": 0,
                "partial": False,
                "error_code": "QuotaExceeded",
                "error_message": discover.get("error"),
            }

        candidate_ids = discover.get("external_ids") or []
        known = await self._content.get_known_external_ids(Platform.YOUTUBE, candidate_ids)
        external_ids = [vid for vid in candidate_ids if vid not in known]
        items_processed = 0
        partial = bool(discover.get("error"))

        if external_ids:
            raw_items = await self._adapter.fetch_item_details(external_ids)
            for raw in raw_items:
                normalized = self._adapter.normalize_item(raw)
                _, is_new = await self._content.upsert_content(
                    platform=Platform.YOUTUBE,
                    normalized=normalized,
                    source_watch_item_id=item.id,
                )
                if is_new:
                    items_processed += 1

        config_patch: dict[str, Any] = {}
        if discover.get("next_cursor"):
            config_patch["page_token"] = discover["next_cursor"]
        if discover.get("resolved_channel_id"):
            resolved = discover["resolved_channel_id"]
            await self._watchlist.update_crawl_status(
                item,
                success=True,
                partial=partial,
                config_patch=config_patch,
                external_id=resolved,
            )
        else:
            await self._watchlist.update_crawl_status(
                item,
                success=True,
                partial=partial,
                config_patch=config_patch,
            )

        return {
            "items_processed": items_processed,
            "partial": partial,
            "error_code": "PartialError" if partial else None,
            "error_message": discover.get("error"),
        }

    async def crawl_tier(
        self,
        tier: WatchTier,
        *,
        item_types: set[WatchItemType] | None = None,
    ) -> dict[str, Any]:
        items = await self._watchlist.list_items(tier=tier, enabled_only=True)
        if item_types:
            items = [i for i in items if i.type in item_types]

        summary = {
            "tier": tier.value,
            "total": len(items),
            "succeeded": 0,
            "failed": 0,
            "new_items": 0,
            "errors": [],
        }

        for item in items:
            if self._adapter.quota_exhausted and item.type in {
                WatchItemType.KEYWORD,
                WatchItemType.ANIME,
            }:
                summary["errors"].append(f"skipped {item.name}: quota exhausted")
                continue
            try:
                job = await self.crawl_watch_item(item.id)
                if job.status in {CrawlJobStatus.SUCCESS, CrawlJobStatus.PARTIAL}:
                    summary["succeeded"] += 1
                    summary["new_items"] += job.items_processed
                else:
                    summary["failed"] += 1
            except QuotaExceededError:
                self._adapter._quota_exhausted = True  # noqa: SLF001
                summary["errors"].append(f"quota exhausted at {item.name}")
                if item.type in {WatchItemType.KEYWORD, WatchItemType.ANIME}:
                    break
            except Exception as exc:  # noqa: BLE001
                summary["failed"] += 1
                summary["errors"].append(f"{item.name}: {exc}")
                logger.exception("tier crawl item failed: %s", item.name)

        return summary


async def create_youtube_ingestion(session: AsyncSession) -> tuple[IngestionService, YouTubeAdapter]:
    settings = get_settings()
    client = YouTubeClient(
        settings.youtube_api_key,
        max_search_calls=settings.youtube_max_search_calls,
        daily_quota_limit=settings.youtube_daily_quota_limit,
    )
    adapter = YouTubeAdapter(client)
    return IngestionService(session, adapter, settings), adapter
