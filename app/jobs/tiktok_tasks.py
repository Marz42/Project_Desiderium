"""Isolated scheduled crawl tasks for TikTok (experimental)."""

from __future__ import annotations

import logging
import uuid

from app.config import get_settings
from app.db import get_session_factory
from app.jobs.mutex import acquire_batch_mutex, get_process_lock, release_batch_mutex
from app.models import CrawlJobAdapter, CrawlJobType, WatchItemType, WatchTier
from app.repositories.watchlist import CrawlJobRepository
from app.services.tiktok_ingestion import create_tiktok_ingestion

logger = logging.getLogger(__name__)


async def crawl_tiktok_accounts() -> None:
    """Experimental TikTok account crawl — isolated from YouTube."""
    settings = get_settings()
    if not settings.tiktok_enabled:
        logger.debug("crawl_tiktok_accounts skipped: TIKTOK_ENABLED=false")
        return

    await _run_tiktok_batch(
        job_name="crawl_tiktok_accounts",
        tier=None,
        item_types={WatchItemType.ACCOUNT},
    )


async def crawl_tiktok_keywords() -> None:
    """Experimental TikTok keyword/anime crawl."""
    settings = get_settings()
    if not settings.tiktok_enabled:
        logger.debug("crawl_tiktok_keywords skipped: TIKTOK_ENABLED=false")
        return

    await _run_tiktok_batch(
        job_name="crawl_tiktok_keywords",
        tier=None,
        item_types={WatchItemType.KEYWORD, WatchItemType.ANIME},
    )


async def crawl_tiktok_rankings() -> None:
    """Experimental TikTok tag/list crawl."""
    settings = get_settings()
    if not settings.tiktok_enabled:
        logger.debug("crawl_tiktok_rankings skipped: TIKTOK_ENABLED=false")
        return

    await _run_tiktok_batch(
        job_name="crawl_tiktok_rankings",
        tier=None,
        item_types={WatchItemType.RANKING},
    )


async def retry_failed_tiktok_crawls() -> None:
    """Retry failed TikTok crawl jobs — independent from YouTube retry."""
    settings = get_settings()
    if not settings.tiktok_enabled:
        return

    session_factory = get_session_factory()
    lock = get_process_lock("crawl_tiktok_retry")
    if lock.locked():
        return

    async with lock:
        async with session_factory() as session:
            jobs_repo = CrawlJobRepository(session)
            failed = await jobs_repo.list_failed_retryable(adapter=CrawlJobAdapter.TIKTOK)
            if not failed:
                return

            try:
                ingestion, adapter = await create_tiktok_ingestion(session)
            except RuntimeError:
                return

            try:
                for job in failed:
                    if job.watch_item_id is None:
                        continue
                    await jobs_repo.increment_retry(job)
                    try:
                        await ingestion.crawl_watch_item(job.watch_item_id)
                    except Exception:  # noqa: BLE001
                        logger.exception(
                            "TikTok retry failed for job %s",
                            job.id,
                            extra={"service": "tiktok", "component": "retry", "alert": True},
                        )
            finally:
                await adapter.close()


async def crawl_single_tiktok_item(watch_item_id: uuid.UUID) -> dict:
    """Manual trigger for a single TikTok watch item."""
    settings = get_settings()
    if not settings.tiktok_enabled:
        return {"status": "disabled", "error_message": "TIKTOK_ENABLED=false"}

    session_factory = get_session_factory()
    async with session_factory() as session:
        ingestion, adapter = await create_tiktok_ingestion(session)
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


async def _run_tiktok_batch(
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
                adapter=CrawlJobAdapter.TIKTOK,
                job_type=CrawlJobType.DISCOVER,
            )
            if not acquired:
                return

            try:
                ingestion, adapter = await create_tiktok_ingestion(session)
            except RuntimeError as exc:
                logger.info("%s skipped: %s", job_name, exc)
                await release_batch_mutex(session, job_name)
                return

            try:
                summary = await ingestion.crawl_batch(tier=tier, item_types=item_types)
                if summary.get("errors"):
                    logger.warning(
                        "%s completed with errors",
                        job_name,
                        extra={
                            "service": "tiktok",
                            "component": job_name,
                            "alert": summary.get("failed", 0) > 0,
                            **summary,
                        },
                    )
                else:
                    logger.info(
                        "%s completed",
                        job_name,
                        extra={"service": "tiktok", "component": job_name, **summary},
                    )
            except Exception:  # noqa: BLE001
                logger.exception(
                    "%s failed",
                    job_name,
                    extra={"service": "tiktok", "component": job_name, "alert": True},
                )
            finally:
                await adapter.close()
                await release_batch_mutex(session, job_name)
