"""Repositories for ops monitoring: heartbeats, quota, LLM usage, job failures."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any, cast

from sqlalchemy import CursorResult, delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ApiQuotaDaily,
    CrawlJob,
    CrawlJobStatus,
    LlmUsageLog,
    MetricSnapshot,
    WorkerHeartbeat,
)


class OpsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_heartbeat(
        self,
        component: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> WorkerHeartbeat:
        now = datetime.now(UTC)
        stmt = insert(WorkerHeartbeat).values(
            component=component,
            last_seen_at=now,
            details=details or {},
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[WorkerHeartbeat.component],
            set_={"last_seen_at": now, "details": details or {}},
        )
        await self._session.execute(stmt)
        await self._session.flush()
        row = await self._session.get(WorkerHeartbeat, component)
        assert row is not None
        return row

    async def get_heartbeat(self, component: str) -> WorkerHeartbeat | None:
        return await self._session.get(WorkerHeartbeat, component)

    async def upsert_youtube_quota(
        self,
        *,
        usage_date: date,
        quota_used: int,
        search_calls: int,
        quota_limit: int,
        max_search_calls: int,
        exhausted: bool = False,
    ) -> ApiQuotaDaily:
        stmt = insert(ApiQuotaDaily).values(
            provider="youtube",
            usage_date=usage_date,
            quota_used=quota_used,
            search_calls=search_calls,
            quota_limit=quota_limit,
            max_search_calls=max_search_calls,
            exhausted=exhausted,
            updated_at=datetime.now(UTC),
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_api_quota_daily_provider_date",
            set_={
                "quota_used": quota_used,
                "search_calls": search_calls,
                "quota_limit": quota_limit,
                "max_search_calls": max_search_calls,
                "exhausted": exhausted,
                "updated_at": datetime.now(UTC),
            },
        )
        await self._session.execute(stmt)
        await self._session.flush()
        result = await self._session.scalar(
            select(ApiQuotaDaily).where(
                ApiQuotaDaily.provider == "youtube",
                ApiQuotaDaily.usage_date == usage_date,
            )
        )
        assert result is not None
        return result

    async def get_youtube_quota(self, usage_date: date | None = None) -> ApiQuotaDaily | None:
        usage_date = usage_date or datetime.now(UTC).date()
        return await self._session.scalar(
            select(ApiQuotaDaily).where(
                ApiQuotaDaily.provider == "youtube",
                ApiQuotaDaily.usage_date == usage_date,
            )
        )

    async def record_llm_usage(
        self,
        *,
        job_name: str,
        prompt_name: str | None,
        model: str | None,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        cost_usd_estimate: float | None = None,
    ) -> LlmUsageLog:
        row = LlmUsageLog(
            job_name=job_name,
            prompt_name=prompt_name,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd_estimate=cost_usd_estimate,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def llm_usage_summary(self, since: datetime) -> dict[str, Any]:
        stmt = select(
            func.count(LlmUsageLog.id),
            func.coalesce(func.sum(LlmUsageLog.prompt_tokens), 0),
            func.coalesce(func.sum(LlmUsageLog.completion_tokens), 0),
            func.coalesce(func.sum(LlmUsageLog.total_tokens), 0),
            func.coalesce(func.sum(LlmUsageLog.cost_usd_estimate), 0.0),
        ).where(LlmUsageLog.created_at >= since)
        row = (await self._session.execute(stmt)).one()
        return {
            "requests": int(row[0] or 0),
            "prompt_tokens": int(row[1] or 0),
            "completion_tokens": int(row[2] or 0),
            "total_tokens": int(row[3] or 0),
            "cost_usd_estimate": round(float(row[4] or 0.0), 6),
        }

    async def crawl_failure_summary(self, since: datetime) -> dict[str, Any]:
        failed_stmt = (
            select(CrawlJob.adapter, func.count())
            .where(
                CrawlJob.status == CrawlJobStatus.FAILED,
                CrawlJob.finished_at >= since,
            )
            .group_by(CrawlJob.adapter)
        )
        failed_by_adapter = {
            adapter.value: int(count)
            for adapter, count in (await self._session.execute(failed_stmt)).all()
        }

        running_stmt = (
            select(func.count())
            .select_from(CrawlJob)
            .where(
                CrawlJob.status == CrawlJobStatus.RUNNING,
            )
        )
        running = int(await self._session.scalar(running_stmt) or 0)

        recent_failed_stmt = (
            select(CrawlJob)
            .where(
                CrawlJob.status == CrawlJobStatus.FAILED,
                CrawlJob.finished_at >= since,
            )
            .order_by(CrawlJob.finished_at.desc())
            .limit(10)
        )
        recent = list((await self._session.scalars(recent_failed_stmt)).all())

        return {
            "failed_by_adapter": failed_by_adapter,
            "failed_total": sum(failed_by_adapter.values()),
            "running": running,
            "recent_failures": [
                {
                    "id": str(job.id),
                    "adapter": job.adapter.value,
                    "job_type": job.job_type.value,
                    "error_code": job.error_code,
                    "error_message": (job.error_message or "")[:200],
                    "finished_at": job.finished_at.isoformat() if job.finished_at else None,
                }
                for job in recent
            ],
        }

    async def purge_metric_snapshots_before(self, cutoff: datetime) -> int:
        stmt = delete(MetricSnapshot).where(MetricSnapshot.captured_at < cutoff)
        result = cast(CursorResult[Any], await self._session.execute(stmt))
        return int(result.rowcount or 0)

    async def count_metric_snapshots(self) -> int:
        return int(
            await self._session.scalar(select(func.count()).select_from(MetricSnapshot)) or 0
        )

    async def snapshots_older_than(self, cutoff: datetime) -> int:
        stmt = (
            select(func.count())
            .select_from(MetricSnapshot)
            .where(
                MetricSnapshot.captured_at < cutoff,
            )
        )
        return int(await self._session.scalar(stmt) or 0)
