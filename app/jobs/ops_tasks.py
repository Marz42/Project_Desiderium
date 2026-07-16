"""Ops maintenance jobs: snapshot retention and disk monitoring."""

from __future__ import annotations

import logging

from app.config import get_settings
from app.db import get_session_factory
from app.jobs.mutex import get_process_lock
from app.repositories.ops import OpsRepository
from app.services.snapshot_retention import purge_old_snapshots
from app.services.system_health import disk_usage

logger = logging.getLogger(__name__)


async def purge_stale_metric_snapshots() -> None:
    lock = get_process_lock("snapshot_retention")
    if lock.locked():
        logger.info("snapshot_retention skipped: already running")
        return

    async with lock:
        session_factory = get_session_factory()
        async with session_factory() as session:
            summary = await purge_old_snapshots(session)
            await session.commit()
            logger.info(
                "snapshot_retention job finished",
                extra={"service": "worker", "component": "snapshot_retention", **summary},
            )


async def monitor_disk_space() -> None:
    settings = get_settings()
    usage = disk_usage("/")
    status = "ok"
    if usage["used_percent"] >= settings.disk_warn_percent:
        status = "warn"
        logger.warning(
            "disk usage above threshold",
            extra={
                "service": "worker",
                "component": "disk_monitor",
                "used_percent": usage["used_percent"],
                "threshold": settings.disk_warn_percent,
            },
        )

    session_factory = get_session_factory()
    async with session_factory() as session:
        repo = OpsRepository(session)
        await repo.upsert_heartbeat(
            "disk_monitor",
            details={"disk": usage, "status": status},
        )
        await session.commit()
