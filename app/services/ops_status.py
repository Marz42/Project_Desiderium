"""Admin ops dashboard data aggregation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.repositories.ops import OpsRepository
from app.services.snapshot_retention import retention_days
from app.services.system_health import collect_health, disk_usage


class OpsStatusService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._repo = OpsRepository(session)

    async def get_status(self, *, disk_path: str = "/") -> dict[str, Any]:
        since = datetime.now(UTC) - timedelta(hours=24)
        failures = await self._repo.crawl_failure_summary(since)
        youtube = await self._repo.get_youtube_quota()
        llm_today = await self._repo.llm_usage_summary(
            datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0),
        )
        health = await collect_health(self._session, disk_path=disk_path, settings=self._settings)
        snapshot_total = await self._repo.count_metric_snapshots()
        retention = retention_days(settings=self._settings)

        youtube_quota_usage = None
        if youtube is not None:
            youtube_quota_usage = {
                "provider": youtube.provider,
                "usage_date": youtube.usage_date.isoformat(),
                "quota_used": youtube.quota_used,
                "quota_limit": youtube.quota_limit,
                "search_calls": youtube.search_calls,
                "max_search_calls": youtube.max_search_calls,
                "exhausted": youtube.exhausted,
                "utilization_percent": round(
                    (youtube.quota_used / youtube.quota_limit) * 100,
                    2,
                )
                if youtube.quota_limit
                else None,
                "updated_at": youtube.updated_at.isoformat(),
            }

        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "environment": self._settings.environment,
            "health": health,
            "task_failures_24h": failures,
            "youtube_quota_usage": youtube_quota_usage,
            "llm_usage_today": llm_today,
            "metric_snapshots": {
                "total": snapshot_total,
                "retention_days": retention,
            },
            "disk": disk_usage(disk_path),
        }
