from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.trend_metrics import hour_bucket
from app.models import ContentItem, MetricSnapshot, Platform, SourceQuality


class MetricsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_latest_snapshot(self, content_item_id: uuid.UUID) -> MetricSnapshot | None:
        stmt = (
            select(MetricSnapshot)
            .where(MetricSnapshot.content_item_id == content_item_id)
            .order_by(desc(MetricSnapshot.captured_at))
            .limit(1)
        )
        return await self._session.scalar(stmt)

    async def list_snapshots_for_content(
        self,
        content_item_id: uuid.UUID,
        *,
        limit: int = 50,
    ) -> list[MetricSnapshot]:
        stmt = (
            select(MetricSnapshot)
            .where(MetricSnapshot.content_item_id == content_item_id)
            .order_by(desc(MetricSnapshot.captured_at))
            .limit(limit)
        )
        result = await self._session.scalars(stmt)
        return list(result.all())

    async def upsert_snapshot(
        self,
        *,
        content_item_id: uuid.UUID,
        captured_at: datetime,
        views: int,
        likes: int | None = None,
        comments: int | None = None,
        shares: int | None = None,
        favorites: int | None = None,
        source_quality: SourceQuality = SourceQuality.OFFICIAL_API,
    ) -> tuple[MetricSnapshot, bool, dict[str, Any]]:
        """Insert or skip snapshot. Returns (row, created, diagnostics)."""
        if captured_at.tzinfo is None:
            captured_at = captured_at.replace(tzinfo=UTC)
        bucket = hour_bucket(captured_at)
        previous = await self.get_latest_snapshot(content_item_id)

        diagnostics: dict[str, Any] = {
            "incremental_views": None,
            "negative_increment": False,
            "anomaly": False,
        }

        if previous is not None:
            incremental = views - int(previous.views)
            diagnostics["incremental_views"] = incremental
            if incremental < 0:
                diagnostics["negative_increment"] = True
                diagnostics["anomaly"] = True

        values = {
            "content_item_id": content_item_id,
            "captured_at": captured_at,
            "captured_at_bucket": bucket,
            "views": views,
            "likes": likes,
            "comments": comments,
            "shares": shares,
            "favorites": favorites,
            "source_quality": source_quality,
        }

        stmt = (
            insert(MetricSnapshot)
            .values(**values)
            .on_conflict_do_nothing(
                index_elements=["content_item_id", "captured_at_bucket"],
            )
            .returning(MetricSnapshot.id)
        )
        result = await self._session.execute(stmt)
        row_id = result.scalar_one_or_none()

        if row_id is None:
            existing_stmt = select(MetricSnapshot).where(
                MetricSnapshot.content_item_id == content_item_id,
                MetricSnapshot.captured_at_bucket == bucket,
            )
            existing = await self._session.scalar(existing_stmt)
            assert existing is not None
            return existing, False, diagnostics

        row = await self._session.get(MetricSnapshot, row_id)
        assert row is not None
        return row, True, diagnostics

    async def list_recent_content_with_snapshots(
        self,
        *,
        lookback_days: int,
        platform: Platform = Platform.YOUTUBE,
    ) -> list[tuple[ContentItem, MetricSnapshot | None]]:
        cutoff = datetime.now(UTC) - timedelta(days=lookback_days)
        latest_subq = (
            select(
                MetricSnapshot.content_item_id,
                func.max(MetricSnapshot.captured_at).label("max_captured_at"),
            )
            .group_by(MetricSnapshot.content_item_id)
            .subquery()
        )

        stmt = (
            select(ContentItem, MetricSnapshot)
            .outerjoin(
                latest_subq,
                ContentItem.id == latest_subq.c.content_item_id,
            )
            .outerjoin(
                MetricSnapshot,
                (MetricSnapshot.content_item_id == ContentItem.id)
                & (MetricSnapshot.captured_at == latest_subq.c.max_captured_at),
            )
            .where(
                ContentItem.platform == platform,
                ContentItem.published_at.is_not(None),
                ContentItem.published_at >= cutoff,
            )
        )
        result = await self._session.execute(stmt)
        return list(result.all())

    async def list_content_for_baseline(
        self,
        *,
        lookback_days: int = 7,
        platform: Platform = Platform.YOUTUBE,
    ) -> list[ContentItem]:
        cutoff = datetime.now(UTC) - timedelta(days=lookback_days)
        stmt = select(ContentItem).where(
            ContentItem.platform == platform,
            ContentItem.published_at.is_not(None),
            ContentItem.published_at >= cutoff,
            ContentItem.channel_external_id.is_not(None),
        )
        result = await self._session.scalars(stmt)
        return list(result.all())
