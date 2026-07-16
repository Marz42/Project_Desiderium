"""Admin trend detail page data."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.content import ContentRepository
from app.repositories.creative_angles import CreativeAngleRepository
from app.repositories.metrics import MetricsRepository
from app.repositories.trends import TrendsRepository
from app.services.angle_status import AngleStatusService


class AdminTrendsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._trends = TrendsRepository(session)
        self._angles = CreativeAngleRepository(session)
        self._content = ContentRepository(session)
        self._metrics = MetricsRepository(session)
        self._status = AngleStatusService(session)

    async def get_detail(self, trend_id: uuid.UUID) -> dict[str, Any] | None:
        trend = await self._trends.get_by_id(trend_id)
        if trend is None:
            return None

        snapshots = await self._trends.list_score_snapshots(trend_id)
        members = await self._trends.list_members_with_content(trend_id)
        angles = await self._angles.list_for_trend(trend_id)

        member_rows: list[dict[str, Any]] = []
        channel_counts: dict[str, int] = {}
        for member in members:
            item = member.content_item
            if item is None:
                continue
            channel = item.channel_name or item.channel_external_id or "unknown"
            channel_counts[channel] = channel_counts.get(channel, 0) + 1
            latest = await self._metrics.get_latest_snapshot(item.id)
            member_rows.append(
                {
                    "member": member,
                    "content": item,
                    "latest_views": latest.views if latest else None,
                    "evidence": member.evidence or {},
                },
            )

        timeline = [
            {
                "date": snap.snapshot_date,
                "score": snap.score,
                "lifecycle_status": snap.lifecycle_status.value,
                "member_count": snap.member_count,
                "channel_count": snap.channel_count,
            }
            for snap in reversed(snapshots)
        ]

        channel_distribution = sorted(
            [{"channel": k, "count": v} for k, v in channel_counts.items()],
            key=lambda row: row["count"],
            reverse=True,
        )

        return {
            "trend": trend,
            "timeline": timeline,
            "score_snapshots": snapshots,
            "members": member_rows,
            "channel_distribution": channel_distribution,
            "angles": angles,
            "score_components": trend.score_components or {},
        }
