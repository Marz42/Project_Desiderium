"""Scheduled crawl tasks for YouTube watchlist ingestion."""

from __future__ import annotations

import logging
import uuid

from app.db import get_session_factory
from app.jobs.mutex import acquire_batch_mutex, get_process_lock, release_batch_mutex
from app.models import CrawlJobAdapter, CrawlJobType, WatchItemType, WatchTier
from app.repositories.watchlist import CrawlJobRepository
from app.services.ingestion import create_youtube_ingestion

logger = logging.getLogger(__name__)


async def crawl_priority_channels() -> None:
    """Priority channels: every 4-6 hours (configured as 5h interval)."""
    await _run_batch_crawl(
        job_name="crawl_priority",
        tier=WatchTier.PRIORITY,
        item_types={WatchItemType.CHANNEL, WatchItemType.ACCOUNT},
    )


async def crawl_general_channels() -> None:
    """General channels: every 12-24 hours (configured as 18h interval)."""
    await _run_batch_crawl(
        job_name="crawl_general",
        tier=WatchTier.GENERAL,
        item_types={WatchItemType.CHANNEL, WatchItemType.ACCOUNT},
    )


async def crawl_keywords() -> None:
    """Keyword and anime watch items: daily."""
    await _run_batch_crawl(
        job_name="crawl_keywords",
        tier=None,
        item_types={WatchItemType.KEYWORD, WatchItemType.ANIME},
    )


async def retry_failed_crawls() -> None:
    """Retry failed per-item crawl jobs with retry_count < max."""
    session_factory = get_session_factory()
    lock = get_process_lock("crawl_retry")
    if lock.locked():
        return

    async with lock:
        async with session_factory() as session:
            jobs_repo = CrawlJobRepository(session)
            failed = await jobs_repo.list_failed_retryable(adapter=CrawlJobAdapter.YOUTUBE)
            if not failed:
                return

            ingestion, adapter = await create_youtube_ingestion(session)
            try:
                for job in failed:
                    if job.watch_item_id is None:
                        continue
                    await jobs_repo.increment_retry(job)
                    try:
                        await ingestion.crawl_watch_item(job.watch_item_id)
                    except Exception:  # noqa: BLE001
                        logger.exception("retry failed for job %s", job.id)
            finally:
                await adapter.close()


async def crawl_single_item(watch_item_id: uuid.UUID) -> dict:
    """Manual trigger for a single watch item."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        ingestion, adapter = await create_youtube_ingestion(session)
        try:
            job = await ingestion.crawl_watch_item(watch_item_id)
            return {
                "job_id": str(job.id),
                "status": job.status.value,
                "items_processed": job.items_processed,
                "error_message": job.error_message,
            }
        finally:
            await adapter.close()


async def _run_batch_crawl(
    *,
    job_name: str,
    tier: WatchTier | None,
    item_types: set[WatchItemType],
) -> None:
    session_factory = get_session_factory()
    lock = get_process_lock(job_name)

    if lock.locked():
        logger.info("%s skipped: already running", job_name)
        return

    async with lock:
        async with session_factory() as session:
            acquired = await acquire_batch_mutex(
                session,
                job_name=job_name,
                adapter=CrawlJobAdapter.YOUTUBE,
                job_type=CrawlJobType.DISCOVER,
            )
            if not acquired:
                return

            ingestion, adapter = await create_youtube_ingestion(session)
            try:
                if tier is not None:
                    summary = await ingestion.crawl_tier(tier, item_types=item_types)
                else:
                    summary = await _crawl_all_types(ingestion, item_types)
                logger.info(
                    "%s completed",
                    job_name,
                    extra={"service": "worker", "component": job_name, **summary},
                )
            finally:
                await adapter.close()
                await release_batch_mutex(session, job_name)


async def _crawl_all_types(ingestion, item_types: set[WatchItemType]) -> dict:
    combined = {"total": 0, "succeeded": 0, "failed": 0, "new_items": 0, "errors": []}
    for tier in WatchTier:
        partial = await ingestion.crawl_tier(tier, item_types=item_types)
        combined["total"] += partial["total"]
        combined["succeeded"] += partial["succeeded"]
        combined["failed"] += partial["failed"]
        combined["new_items"] += partial["new_items"]
        combined["errors"].extend(partial["errors"])
        if ingestion._adapter.quota_exhausted:  # noqa: SLF001
            break
    return combined
