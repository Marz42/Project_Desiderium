"""System health probes: database, disk, worker liveness."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import check_database_connection
from app.repositories.ops import OpsRepository


def disk_usage(path: str = "/") -> dict[str, Any]:
    usage = shutil.disk_usage(path)
    used_percent = round((usage.used / usage.total) * 100, 2) if usage.total else 0.0
    return {
        "path": path,
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": usage.free,
        "used_percent": used_percent,
    }


async def worker_status(
    session: AsyncSession,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    repo = OpsRepository(session)
    heartbeat = await repo.get_heartbeat("worker")
    if heartbeat is None:
        return {"status": "unknown", "last_seen_at": None, "stale": True}

    age = datetime.now(UTC) - heartbeat.last_seen_at
    stale_minutes = settings.worker_stale_minutes
    stale = age > timedelta(minutes=stale_minutes)
    return {
        "status": "stale" if stale else "ok",
        "last_seen_at": heartbeat.last_seen_at.isoformat(),
        "age_seconds": int(age.total_seconds()),
        "stale": stale,
        "details": heartbeat.details or {},
    }


async def collect_health(
    session: AsyncSession,
    *,
    disk_path: str = "/",
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    db_ok = await check_database_connection()
    disk = disk_usage(disk_path)
    worker = await worker_status(session, settings=settings)

    disk_status = "ok"
    if disk["used_percent"] >= settings.disk_warn_percent:
        disk_status = "warn"

    overall = "ok"
    if not db_ok or worker.get("stale") or disk_status == "warn":
        overall = "degraded"
    if not db_ok:
        overall = "unavailable"

    return {
        "status": overall,
        "database": "up" if db_ok else "down",
        "disk": {**disk, "status": disk_status},
        "worker": worker,
        "environment": settings.environment,
    }
