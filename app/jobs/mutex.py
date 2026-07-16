"""Job mutex to prevent duplicate batch crawl runs."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CrawlJobAdapter, CrawlJobType
from app.repositories.watchlist import CrawlJobRepository

logger = logging.getLogger(__name__)

# In-process locks keyed by job name
_process_locks: dict[str, asyncio.Lock] = {}


def get_process_lock(name: str) -> asyncio.Lock:
    if name not in _process_locks:
        _process_locks[name] = asyncio.Lock()
    return _process_locks[name]


LOCK_IDS = {
    "crawl_priority": 1001,
    "crawl_general": 1002,
    "crawl_keywords": 1003,
    "crawl_retry": 1004,
    "crawl_tiktok_accounts": 1101,
    "crawl_tiktok_keywords": 1102,
    "crawl_tiktok_rankings": 1103,
    "crawl_tiktok_retry": 1104,
    "metric_snapshots": 1201,
    "trend_discovery": 1202,
    "snapshot_retention": 1203,
}


async def try_advisory_lock(session: AsyncSession, lock_id: int) -> bool:
    result = await session.execute(
        text("SELECT pg_try_advisory_lock(:lock_id)"),
        {"lock_id": lock_id},
    )
    return bool(result.scalar())


async def release_advisory_lock(session: AsyncSession, lock_id: int) -> None:
    await session.execute(
        text("SELECT pg_advisory_unlock(:lock_id)"),
        {"lock_id": lock_id},
    )


async def acquire_batch_mutex(
    session: AsyncSession,
    *,
    job_name: str,
    adapter: CrawlJobAdapter,
    job_type: CrawlJobType,
) -> bool:
    """Try to acquire DB-level mutex for a batch job (caller holds in-process lock)."""
    jobs = CrawlJobRepository(session)
    if await jobs.has_running_batch(adapter, job_type):
        logger.info("batch job %s skipped: another batch running in DB", job_name)
        return False

    lock_id = LOCK_IDS.get(job_name, 1999)
    if not await try_advisory_lock(session, lock_id):
        logger.info("batch job %s skipped: advisory lock held", job_name)
        return False

    return True


async def release_batch_mutex(session: AsyncSession, job_name: str) -> None:
    lock_id = LOCK_IDS.get(job_name, 1999)
    await release_advisory_lock(session, lock_id)
