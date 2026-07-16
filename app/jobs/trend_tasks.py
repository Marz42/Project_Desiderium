"""Scheduled metric snapshot and trend discovery tasks."""

from __future__ import annotations

import logging

from app.db import get_session_factory
from app.jobs.mutex import acquire_batch_mutex, get_process_lock, release_batch_mutex
from app.models import CrawlJobAdapter, CrawlJobType
from app.services.ingestion import create_youtube_ingestion
from app.services.quota_tracker import persist_youtube_quota
from app.services.snapshots import SnapshotService
from app.services.trend_discovery import TrendDiscoveryService

logger = logging.getLogger(__name__)


async def capture_metric_snapshots() -> None:
    """Capture due metric snapshots for recent videos."""
    session_factory = get_session_factory()
    lock = get_process_lock("metric_snapshots")

    if lock.locked():
        logger.info("metric_snapshots skipped: already running")
        return

    async with lock:
        async with session_factory() as session:
            acquired = await acquire_batch_mutex(
                session,
                job_name="metric_snapshots",
                adapter=CrawlJobAdapter.YOUTUBE,
                job_type=CrawlJobType.METRICS,
            )
            if not acquired:
                return

            ingestion, adapter = await create_youtube_ingestion(session)
            try:
                service = SnapshotService(session, adapter)
                summary = await service.capture_snapshots()
                await persist_youtube_quota(
                    session,
                    adapter.quota_summary(),
                    exhausted=adapter.quota_exhausted,
                )
                await session.commit()
                logger.info(
                    "metric_snapshots completed",
                    extra={"service": "worker", "component": "metric_snapshots", **summary},
                )
            finally:
                await adapter.close()
                await release_batch_mutex(session, "metric_snapshots")


async def run_trend_discovery() -> None:
    """Daily trend clustering, scoring, lifecycle, and score snapshots."""
    session_factory = get_session_factory()
    lock = get_process_lock("trend_discovery")

    if lock.locked():
        logger.info("trend_discovery skipped: already running")
        return

    async with lock:
        async with session_factory() as session:
            acquired = await acquire_batch_mutex(
                session,
                job_name="trend_discovery",
                adapter=CrawlJobAdapter.YOUTUBE,
                job_type=CrawlJobType.METRICS,
            )
            if not acquired:
                return

            try:
                service = TrendDiscoveryService(session)
                summary = await service.run_daily_pipeline()
                logger.info(
                    "trend_discovery completed",
                    extra={"service": "worker", "component": "trend_discovery", **summary},
                )
            finally:
                await release_batch_mutex(session, "trend_discovery")
