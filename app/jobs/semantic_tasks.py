"""Scheduled LLM semantic analysis tasks."""

from __future__ import annotations

import logging

from app.config import get_settings
from app.db import get_session_factory
from app.jobs.mutex import acquire_batch_mutex, get_process_lock, release_batch_mutex
from app.models import CrawlJobAdapter, CrawlJobType
from app.services.semantic_analysis import create_semantic_analysis_service

logger = logging.getLogger(__name__)


async def run_semantic_analysis() -> None:
    """Run LLM semantic analysis for scored trends (failures do not block scoring)."""
    settings = get_settings()
    if not settings.llm_api_key:
        logger.info("semantic_analysis skipped: LLM_API_KEY not configured")
        return

    session_factory = get_session_factory()
    lock = get_process_lock("semantic_analysis")

    if lock.locked():
        logger.info("semantic_analysis skipped: already running")
        return

    async with lock:
        async with session_factory() as session:
            acquired = await acquire_batch_mutex(
                session,
                job_name="semantic_analysis",
                adapter=CrawlJobAdapter.TRANSCRIPT,
                job_type=CrawlJobType.TRANSCRIPT,
            )
            if not acquired:
                return

            service = await create_semantic_analysis_service(session)
            try:
                summary = await service.run_daily_semantic_analysis()
                logger.info(
                    "semantic_analysis completed",
                    extra={"service": "worker", "component": "semantic_analysis", **summary},
                )
            finally:
                await service.close()
                await release_batch_mutex(session, "semantic_analysis")
