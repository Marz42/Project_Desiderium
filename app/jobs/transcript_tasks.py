"""Scheduled transcript fetch tasks."""

from __future__ import annotations

import logging

from app.db import get_session_factory
from app.jobs.mutex import acquire_batch_mutex, get_process_lock, release_batch_mutex
from app.models import CrawlJobAdapter, CrawlJobType
from app.services.transcripts import TranscriptService

logger = logging.getLogger(__name__)


async def fetch_priority_transcripts() -> None:
    """Fetch public captions for priority-channel videos (metadata fallback on miss)."""
    session_factory = get_session_factory()
    lock = get_process_lock("transcript_fetch")

    if lock.locked():
        logger.info("transcript_fetch skipped: already running")
        return

    async with lock:
        async with session_factory() as session:
            acquired = await acquire_batch_mutex(
                session,
                job_name="transcript_fetch",
                adapter=CrawlJobAdapter.TRANSCRIPT,
                job_type=CrawlJobType.TRANSCRIPT,
            )
            if not acquired:
                return

            service = TranscriptService(session)
            try:
                summary = await service.fetch_for_priority_candidates()
                logger.info(
                    "transcript_fetch completed",
                    extra={"service": "worker", "component": "transcript_fetch", **summary},
                )
            finally:
                await service.close()
                await release_batch_mutex(session, "transcript_fetch")
