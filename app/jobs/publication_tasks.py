"""Scheduled G4 publication performance feedback job."""

from __future__ import annotations

import logging

from app.db import get_session_factory
from app.jobs.mutex import LOCK_IDS, get_process_lock, release_advisory_lock, try_advisory_lock
from app.services.publication_metrics import PublicationMetricsService

logger = logging.getLogger(__name__)


async def run_publication_metrics() -> None:
    """Fetch due public-metric windows for published videos (association only)."""
    lock = get_process_lock("publication_metrics")
    if lock.locked():
        logger.info("publication_metrics skipped: already running")
        return

    async with lock:
        session_factory = get_session_factory()
        async with session_factory() as session:
            lock_id = LOCK_IDS["publication_metrics"]
            if not await try_advisory_lock(session, lock_id):
                logger.info("publication_metrics skipped: advisory lock held")
                return

            try:
                service = PublicationMetricsService(session)
                summary = await service.run_due_windows()
                logger.info(
                    "publication_metrics job finished",
                    extra={"service": "worker", "component": "publication_metrics", **summary},
                )
            finally:
                await release_advisory_lock(session, lock_id)
