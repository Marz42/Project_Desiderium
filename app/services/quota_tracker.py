"""Persist YouTube API quota usage for cross-process monitoring."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.ops import OpsRepository


async def persist_youtube_quota(
    session: AsyncSession,
    quota_summary: dict[str, int],
    *,
    exhausted: bool = False,
) -> None:
    repo = OpsRepository(session)
    await repo.upsert_youtube_quota(
        usage_date=datetime.now(UTC).date(),
        quota_used=int(quota_summary.get("quota_used_estimate") or 0),
        search_calls=int(quota_summary.get("search_calls") or 0),
        quota_limit=int(quota_summary.get("daily_quota_limit") or 0),
        max_search_calls=int(quota_summary.get("max_search_calls") or 0),
        exhausted=exhausted,
    )
    await session.commit()
