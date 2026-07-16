"""Metric snapshot capture with age-based dynamic scheduling."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.youtube import YouTubeAdapter
from app.domain.trend_metrics import is_snapshot_due
from app.models import Platform, SourceQuality
from app.repositories.metrics import MetricsRepository
from app.services.scoring_config import ScoringConfig, get_scoring_config

logger = logging.getLogger(__name__)


class SnapshotService:
    def __init__(
        self,
        session: AsyncSession,
        adapter: YouTubeAdapter,
        config: ScoringConfig | None = None,
    ) -> None:
        self._session = session
        self._adapter = adapter
        self._metrics = MetricsRepository(session)
        self._config = config or get_scoring_config()

    async def list_due_content_ids(self) -> list[uuid.UUID]:
        rows = await self._metrics.list_recent_content_with_snapshots(
            lookback_days=self._config.snapshots.lookback_days,
        )
        now = datetime.now(UTC)
        due: list[uuid.UUID] = []
        for content, latest_snapshot in rows:
            last_at = latest_snapshot.captured_at if latest_snapshot else None
            if is_snapshot_due(last_at, content.published_at, now, config=self._config):
                due.append(content.id)
        return due

    async def capture_snapshots(
        self,
        content_ids: list[uuid.UUID] | None = None,
    ) -> dict[str, Any]:
        if content_ids is None:
            content_ids = await self.list_due_content_ids()

        if not content_ids:
            return {"requested": 0, "created": 0, "skipped": 0, "anomalies": 0}

        from sqlalchemy import select

        from app.models import ContentItem

        stmt = select(ContentItem).where(ContentItem.id.in_(content_ids))
        items = list((await self._session.scalars(stmt)).all())
        external_by_id = {item.id: item.external_id for item in items}
        external_ids = [item.external_id for item in items]

        metrics_payload = await self._adapter.fetch_metrics(external_ids)
        metrics_by_external = {row["external_id"]: row for row in metrics_payload}

        created = 0
        skipped = 0
        anomalies = 0
        now = datetime.now(UTC)

        for item in items:
            payload = metrics_by_external.get(item.external_id)
            if not payload:
                skipped += 1
                continue
            metrics = payload.get("metrics") or {}
            _, was_created, diagnostics = await self._metrics.upsert_snapshot(
                content_item_id=item.id,
                captured_at=now,
                views=int(metrics.get("views") or 0),
                likes=metrics.get("likes"),
                comments=metrics.get("comments"),
                source_quality=SourceQuality.OFFICIAL_API,
            )
            if was_created:
                created += 1
            else:
                skipped += 1
            if diagnostics.get("anomaly"):
                anomalies += 1
                logger.warning(
                    "metric anomaly for content %s (%s): %s",
                    item.id,
                    external_by_id.get(item.id),
                    diagnostics,
                )

        return {
            "requested": len(content_ids),
            "created": created,
            "skipped": skipped,
            "anomalies": anomalies,
        }
