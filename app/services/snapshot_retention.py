"""Purge metric snapshots older than the configured retention window."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.repositories.ops import OpsRepository
from app.services.scoring_config import ScoringConfig, get_scoring_config

logger = logging.getLogger(__name__)


def retention_days(config: ScoringConfig | None = None, settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    config = config or get_scoring_config()
    return getattr(config.snapshots, "retention_days", None) or settings.snapshot_retention_days


async def purge_old_snapshots(
    session: AsyncSession,
    *,
    config: ScoringConfig | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    days = retention_days(config, settings)
    cutoff = datetime.now(UTC) - timedelta(days=days)
    repo = OpsRepository(session)
    eligible = await repo.snapshots_older_than(cutoff)
    deleted = await repo.purge_metric_snapshots_before(cutoff)
    remaining = await repo.count_metric_snapshots()
    summary = {
        "retention_days": days,
        "cutoff": cutoff.isoformat(),
        "eligible": eligible,
        "deleted": deleted,
        "remaining": remaining,
    }
    logger.info(
        "snapshot retention purge completed",
        extra={"service": "worker", "component": "snapshot_retention", **summary},
    )
    return summary
