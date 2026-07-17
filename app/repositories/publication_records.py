"""Publication record and metric snapshot repositories (G4)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    AgeBucket,
    BaselineConfidence,
    CreativeFormat,
    Platform,
    PublicationFetchStatus,
    PublicationMetricSnapshot,
    PublicationRecord,
    PublicationStatus,
    PublicationWindowKey,
)


class PublicationRecordRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, record_id: uuid.UUID) -> PublicationRecord | None:
        return await self._session.get(PublicationRecord, record_id)

    async def list_published_for_metrics(self) -> list[PublicationRecord]:
        """Published records with a resolvable video ID, for the metrics job."""
        stmt = (
            select(PublicationRecord)
            .where(
                PublicationRecord.status == PublicationStatus.PUBLISHED,
                PublicationRecord.external_video_id.is_not(None),
                PublicationRecord.terminal_fetch_failure.is_(False),
                (
                    PublicationRecord.next_retry_at.is_(None)
                    | (PublicationRecord.next_retry_at <= datetime.now(UTC))
                ),
            )
            .options(selectinload(PublicationRecord.metric_snapshots))
            .order_by(PublicationRecord.created_at)
        )
        return list((await self._session.scalars(stmt)).all())

    async def list_published_with_snapshots(self) -> list[PublicationRecord]:
        """Published records with full relations, for performance analytics."""
        stmt = (
            select(PublicationRecord)
            .where(PublicationRecord.status == PublicationStatus.PUBLISHED)
            .options(
                selectinload(PublicationRecord.metric_snapshots),
                selectinload(PublicationRecord.creative_angle),
                selectinload(PublicationRecord.trend),
                selectinload(PublicationRecord.daily_candidate),
            )
            .order_by(PublicationRecord.created_at)
        )
        return list((await self._session.scalars(stmt)).all())

    async def update_enrichment(
        self,
        record: PublicationRecord,
        *,
        channel_external_id: str | None = None,
        published_at: datetime | None = None,
        format: CreativeFormat | None = None,
        platform: Platform | None = None,
        fetch_status: PublicationFetchStatus | None = None,
        last_fetch_error: str | None = None,
        last_fetched_at: datetime | None = None,
    ) -> PublicationRecord:
        if channel_external_id is not None:
            record.channel_external_id = channel_external_id
        if published_at is not None:
            record.published_at = published_at
        if format is not None:
            record.format = format
        if platform is not None:
            record.platform = platform
        if fetch_status is not None:
            record.fetch_status = fetch_status
        record.last_fetch_error = last_fetch_error
        if last_fetched_at is not None:
            record.last_fetched_at = last_fetched_at
        await self._session.flush()
        return record


class PublicationMetricSnapshotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_record(
        self,
        publication_record_id: uuid.UUID,
    ) -> list[PublicationMetricSnapshot]:
        stmt = (
            select(PublicationMetricSnapshot)
            .where(PublicationMetricSnapshot.publication_record_id == publication_record_id)
            .order_by(PublicationMetricSnapshot.captured_at)
        )
        return list((await self._session.scalars(stmt)).all())

    async def upsert(
        self,
        *,
        publication_record_id: uuid.UUID,
        window_key: PublicationWindowKey,
        captured_at: datetime,
        video_age_hours: float,
        age_bucket: AgeBucket | None,
        views: int,
        likes: int | None,
        comments: int | None,
        source: str,
        late_backfill: bool,
        baseline_velocity: float | None,
        baseline_sample_count: int | None,
        baseline_confidence: BaselineConfidence | None,
        performance_ratio: float | None,
        baseline_version: str,
        calculated_at: datetime,
    ) -> PublicationMetricSnapshot:
        values: dict[str, Any] = {
            "id": uuid.uuid4(),
            "publication_record_id": publication_record_id,
            "window_key": window_key,
            "captured_at": captured_at,
            "video_age_hours": video_age_hours,
            "age_bucket": age_bucket,
            "views": views,
            "likes": likes,
            "comments": comments,
            "source": source,
            "late_backfill": late_backfill,
            "baseline_velocity": baseline_velocity,
            "baseline_sample_count": baseline_sample_count,
            "baseline_confidence": baseline_confidence,
            "performance_ratio": performance_ratio,
            "baseline_version": baseline_version,
            "calculated_at": calculated_at,
            "observed_ratio_at_window": performance_ratio,
        }
        stmt = (
            insert(PublicationMetricSnapshot)
            .values(**values)
            .on_conflict_do_nothing(
                constraint="uq_publication_metric_snapshots_record_window",
            )
            .returning(PublicationMetricSnapshot.id)
        )
        row_id = (await self._session.execute(stmt)).scalar_one_or_none()
        if row_id is None:
            existing = await self._session.scalar(
                select(PublicationMetricSnapshot).where(
                    PublicationMetricSnapshot.publication_record_id
                    == publication_record_id,
                    PublicationMetricSnapshot.window_key == window_key,
                ),
            )
            assert existing is not None
            return existing
        snapshot = await self._session.get(PublicationMetricSnapshot, row_id)
        assert snapshot is not None
        return snapshot

    async def list_baseline_candidates(
        self,
        *,
        format: CreativeFormat,
        age_bucket: AgeBucket,
        team_channel_ids: tuple[str, ...],
        exclude_record_id: uuid.UUID | None,
    ) -> list[tuple[float, float]]:
        """Return (views, video_age_hours) pairs for baseline velocity calc."""
        stmt = (
            select(PublicationMetricSnapshot.views, PublicationMetricSnapshot.video_age_hours)
            .join(
                PublicationRecord,
                PublicationMetricSnapshot.publication_record_id == PublicationRecord.id,
            )
            .where(
                PublicationRecord.format == format,
                PublicationMetricSnapshot.age_bucket == age_bucket,
            )
        )
        if team_channel_ids:
            stmt = stmt.where(PublicationRecord.channel_external_id.in_(team_channel_ids))
        if exclude_record_id is not None:
            stmt = stmt.where(PublicationRecord.id != exclude_record_id)
        rows = (await self._session.execute(stmt)).all()
        return [(float(views), float(age)) for views, age in rows]

    async def list_aggregate_candidates(
        self,
        *,
        team_channel_ids: tuple[str, ...],
        exclude_record_id: uuid.UUID | None,
    ) -> list[tuple[float, float]]:
        """Team-wide fallback sample, ignoring format/age_bucket grouping."""
        stmt = select(
            PublicationMetricSnapshot.views,
            PublicationMetricSnapshot.video_age_hours,
        ).join(
            PublicationRecord,
            PublicationMetricSnapshot.publication_record_id == PublicationRecord.id,
        )
        if team_channel_ids:
            stmt = stmt.where(PublicationRecord.channel_external_id.in_(team_channel_ids))
        if exclude_record_id is not None:
            stmt = stmt.where(PublicationRecord.id != exclude_record_id)
        rows = (await self._session.execute(stmt)).all()
        return [(float(views), float(age)) for views, age in rows]
