from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    CrawlJob,
    CrawlJobAdapter,
    CrawlJobStatus,
    CrawlJobType,
    CrawlOutcome,
    WatchItem,
    WatchTier,
)
from app.schemas.watchlist import WatchItemCreate, WatchItemUpdate


class WatchlistRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def count(self) -> int:
        result = await self._session.scalar(select(func.count()).select_from(WatchItem))
        return int(result or 0)

    async def get_by_id(self, item_id: uuid.UUID) -> WatchItem | None:
        return await self._session.get(WatchItem, item_id)

    async def find_by_unique_key(
        self,
        platform: str,
        item_type: str,
        external_id: str,
    ) -> WatchItem | None:
        stmt = select(WatchItem).where(
            WatchItem.platform == platform,
            WatchItem.type == item_type,
            WatchItem.external_id == external_id,
        )
        return await self._session.scalar(stmt)

    async def list_items(
        self,
        *,
        tier: WatchTier | None = None,
        enabled_only: bool = False,
        limit: int = 200,
        offset: int = 0,
    ) -> list[WatchItem]:
        stmt = select(WatchItem).order_by(WatchItem.tier, WatchItem.name)
        if tier is not None:
            stmt = stmt.where(WatchItem.tier == tier)
        if enabled_only:
            stmt = stmt.where(WatchItem.enabled.is_(True))
        stmt = stmt.limit(limit).offset(offset)
        result = await self._session.scalars(stmt)
        return list(result.all())

    async def create(self, data: WatchItemCreate) -> WatchItem:
        item = WatchItem(
            type=data.type,
            platform=data.platform,
            name=data.name,
            external_id=data.external_id,
            url=data.url,
            tier=data.tier,
            tags=data.tags,
            note=data.note,
            enabled=data.enabled,
            config=data.config,
        )
        self._session.add(item)
        await self._session.flush()
        return item

    async def update(self, item: WatchItem, data: WatchItemUpdate) -> WatchItem:
        if data.name is not None:
            item.name = data.name
        if data.url is not None:
            item.url = data.url
        if data.tier is not None:
            item.tier = data.tier
        if data.tags is not None:
            item.tags = data.tags
        if data.note is not None:
            item.note = data.note
        if data.enabled is not None:
            item.enabled = data.enabled
        if data.config is not None:
            item.config = data.config
        item.updated_at = datetime.now(UTC)
        await self._session.flush()
        return item

    async def delete(self, item: WatchItem) -> None:
        await self._session.delete(item)

    async def update_crawl_status(
        self,
        item: WatchItem,
        *,
        success: bool,
        partial: bool = False,
        config_patch: dict[str, Any] | None = None,
        external_id: str | None = None,
    ) -> WatchItem:
        now = datetime.now(UTC)
        item.last_attempt_at = now
        if success:
            item.last_success_at = now
            item.last_status = CrawlOutcome.PARTIAL if partial else CrawlOutcome.SUCCESS
            item.consecutive_failures = 0
        else:
            item.last_status = CrawlOutcome.FAILED
            item.consecutive_failures += 1
        if config_patch:
            merged = dict(item.config or {})
            merged.update(config_patch)
            item.config = merged
        if external_id:
            item.external_id = external_id
        item.updated_at = now
        await self._session.flush()
        return item


class CrawlJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        adapter: CrawlJobAdapter,
        job_type: CrawlJobType,
        watch_item_id: uuid.UUID | None = None,
    ) -> CrawlJob:
        job = CrawlJob(
            adapter=adapter,
            job_type=job_type,
            watch_item_id=watch_item_id,
            status=CrawlJobStatus.QUEUED,
        )
        self._session.add(job)
        await self._session.flush()
        return job

    async def start(self, job: CrawlJob) -> CrawlJob:
        job.status = CrawlJobStatus.RUNNING
        job.started_at = datetime.now(UTC)
        await self._session.flush()
        return job

    async def finish(
        self,
        job: CrawlJob,
        *,
        status: CrawlJobStatus,
        items_processed: int = 0,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> CrawlJob:
        job.status = status
        job.finished_at = datetime.now(UTC)
        job.items_processed = items_processed
        job.error_code = error_code
        job.error_message = error_message
        await self._session.flush()
        return job

    async def increment_retry(self, job: CrawlJob) -> CrawlJob:
        job.retry_count += 1
        await self._session.flush()
        return job

    async def has_running_batch(self, adapter: CrawlJobAdapter, job_type: CrawlJobType) -> bool:
        stmt = select(func.count()).select_from(CrawlJob).where(
            CrawlJob.adapter == adapter,
            CrawlJob.job_type == job_type,
            CrawlJob.status == CrawlJobStatus.RUNNING,
            CrawlJob.watch_item_id.is_(None),
        )
        count = await self._session.scalar(stmt)
        return int(count or 0) > 0

    async def list_recent_for_item(
        self,
        watch_item_id: uuid.UUID,
        *,
        limit: int = 10,
    ) -> list[CrawlJob]:
        stmt = (
            select(CrawlJob)
            .where(CrawlJob.watch_item_id == watch_item_id)
            .order_by(CrawlJob.created_at.desc())
            .limit(limit)
        )
        result = await self._session.scalars(stmt)
        return list(result.all())

    async def list_failed_retryable(self, *, max_retries: int = 3, limit: int = 20) -> list[CrawlJob]:
        stmt = (
            select(CrawlJob)
            .where(
                CrawlJob.status == CrawlJobStatus.FAILED,
                CrawlJob.retry_count < max_retries,
                CrawlJob.watch_item_id.is_not(None),
            )
            .order_by(CrawlJob.finished_at.asc())
            .limit(limit)
        )
        result = await self._session.scalars(stmt)
        return list(result.all())
