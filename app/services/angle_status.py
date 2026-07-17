"""Angle status state machine with audit trail."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.youtube_url import parse_youtube_video_id
from app.models import (
    AngleStatus,
    AngleStatusAudit,
    Brief,
    BriefItem,
    BriefStatus,
    CreativeAngle,
    Platform,
    PublicationFetchStatus,
    PublicationRecord,
    PublicationStatus,
)

VALID_TRANSITIONS: dict[AngleStatus, set[AngleStatus]] = {
    AngleStatus.CANDIDATE: {AngleStatus.SELECTED, AngleStatus.BLOCKED},
    AngleStatus.SELECTED: {AngleStatus.CANDIDATE, AngleStatus.ADOPTED, AngleStatus.BLOCKED},
    AngleStatus.ADOPTED: {AngleStatus.PUBLISHED, AngleStatus.REUSABLE},
    AngleStatus.PUBLISHED: {AngleStatus.REUSABLE},
    AngleStatus.REUSABLE: set(),
    AngleStatus.BLOCKED: set(),
}


class InvalidStatusTransition(Exception):
    def __init__(self, from_status: AngleStatus | None, to_status: AngleStatus) -> None:
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(f"Cannot transition from {from_status} to {to_status}")


class PublishedUrlRequired(Exception):
    """Raised when transitioning to PUBLISHED without a valid YouTube URL."""

    def __init__(self, published_url: str | None) -> None:
        self.published_url = published_url
        super().__init__(
            "A valid YouTube URL (watch/shorts/youtu.be) is required to mark published"
        )


class PublishedUrlConflict(Exception):
    """Raised when a platform video is already bound to another angle."""

    def __init__(self, video_id: str) -> None:
        self.video_id = video_id
        super().__init__(f"YouTube video {video_id} is already bound to another creative angle")


class PublishedUrlChangeConflict(Exception):
    """Raised when an already-published angle is submitted with a different video."""

    def __init__(self, existing_video_id: str, requested_video_id: str) -> None:
        self.existing_video_id = existing_video_id
        self.requested_video_id = requested_video_id
        super().__init__(
            f"Angle already published as {existing_video_id}; "
            f"cannot rebind to {requested_video_id}",
        )


class AngleStatusService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def can_transition(self, from_status: AngleStatus | None, to_status: AngleStatus) -> bool:
        if from_status is None:
            return True
        if from_status == to_status:
            return True
        return to_status in VALID_TRANSITIONS.get(from_status, set())

    async def transition(
        self,
        angle: CreativeAngle,
        to_status: AngleStatus,
        *,
        note: str | None = None,
        published_url: str | None = None,
        daily_candidate_id: uuid.UUID | None = None,
    ) -> CreativeAngle:
        angle_id = angle.id
        from_status = angle.status
        if from_status != to_status and not self.can_transition(from_status, to_status):
            raise InvalidStatusTransition(from_status, to_status)

        if from_status == to_status:
            if to_status == AngleStatus.PUBLISHED and published_url:
                return await self._handle_published_resubmit(angle, published_url)
            return angle

        video_id: str | None = None
        if to_status == AngleStatus.PUBLISHED:
            video_id = parse_youtube_video_id(published_url)
            if video_id is None:
                raise PublishedUrlRequired(published_url)
            existing = await self._session.scalar(
                select(PublicationRecord).where(
                    PublicationRecord.platform == Platform.YOUTUBE,
                    PublicationRecord.external_video_id == video_id,
                ),
            )
            if existing is not None:
                if existing.creative_angle_id == angle.id:
                    angle.status = AngleStatus.PUBLISHED
                    return angle
                raise PublishedUrlConflict(video_id)

        angle.status = to_status
        self._session.add(
            AngleStatusAudit(
                creative_angle_id=angle.id,
                from_status=from_status,
                to_status=to_status,
                note=note,
            ),
        )
        record = await self._record_publication(
            angle,
            to_status,
            note=note,
            published_url=published_url,
            video_id=video_id,
            daily_candidate_id=daily_candidate_id,
        )
        try:
            await self._session.flush()
        except IntegrityError as exc:
            await self._session.rollback()
            if video_id is not None:
                existing = await self._session.scalar(
                    select(PublicationRecord).where(
                        PublicationRecord.platform == Platform.YOUTUBE,
                        PublicationRecord.external_video_id == video_id,
                    ),
                )
                if existing is not None and existing.creative_angle_id == angle_id:
                    persisted = await self._session.get(CreativeAngle, angle_id)
                    return persisted or angle
                raise PublishedUrlConflict(video_id) from exc
            raise

        if record is not None and video_id is not None:
            # Best-effort enrichment via the public YouTube API. Import kept
            # local to avoid a service->service import cycle at module load.
            from app.services.publication_metrics import PublicationMetricsService

            await PublicationMetricsService(self._session).attempt_immediate_capture(record)

        return angle

    async def _handle_published_resubmit(
        self,
        angle: CreativeAngle,
        published_url: str,
    ) -> CreativeAngle:
        """Idempotent re-submit of the same published URL; reject rebinding."""
        video_id = parse_youtube_video_id(published_url)
        if video_id is None:
            raise PublishedUrlRequired(published_url)
        existing = await self._session.scalar(
            select(PublicationRecord)
            .where(PublicationRecord.creative_angle_id == angle.id)
            .order_by(PublicationRecord.created_at.desc())
            .limit(1),
        )
        if existing is not None and existing.external_video_id:
            if existing.external_video_id == video_id:
                return angle
            raise PublishedUrlChangeConflict(existing.external_video_id, video_id)
        cross = await self._session.scalar(
            select(PublicationRecord).where(
                PublicationRecord.platform == Platform.YOUTUBE,
                PublicationRecord.external_video_id == video_id,
            ),
        )
        if cross is not None and cross.creative_angle_id != angle.id:
            raise PublishedUrlConflict(video_id)
        return angle

    async def _record_publication(
        self,
        angle: CreativeAngle,
        status: AngleStatus,
        *,
        note: str | None,
        published_url: str | None,
        video_id: str | None,
        daily_candidate_id: uuid.UUID | None,
    ) -> PublicationRecord | None:
        pub_map = {
            AngleStatus.ADOPTED: PublicationStatus.ADOPTED,
            AngleStatus.PUBLISHED: PublicationStatus.PUBLISHED,
            AngleStatus.REUSABLE: PublicationStatus.REUSABLE,
            AngleStatus.BLOCKED: PublicationStatus.BLOCKED,
        }
        pub_status = pub_map.get(status)
        if pub_status is None:
            return None

        brief = await self._session.scalar(
            select(Brief)
            .join(BriefItem, BriefItem.brief_id == Brief.id)
            .where(
                BriefItem.creative_angle_id == angle.id,
                Brief.status == BriefStatus.FINALIZED,
            )
            .order_by(Brief.finalized_at.desc().nullslast())
            .limit(1),
        )
        record = PublicationRecord(
            creative_angle_id=angle.id,
            status=pub_status,
            published_url=published_url,
            published_at=datetime.now(UTC) if status == AngleStatus.PUBLISHED else None,
            note=note,
            trend_id=angle.trend_id,
            daily_candidate_id=daily_candidate_id,
            brief_id=brief.id if brief else None,
            brief_finalized_at=brief.finalized_at if brief else None,
            platform=Platform.YOUTUBE if video_id else None,
            external_video_id=video_id,
            fetch_status=PublicationFetchStatus.PENDING if video_id else None,
        )
        self._session.add(record)
        return record

    async def list_audits(self, angle_id: uuid.UUID) -> list[AngleStatusAudit]:
        stmt = (
            select(AngleStatusAudit)
            .where(AngleStatusAudit.creative_angle_id == angle_id)
            .order_by(AngleStatusAudit.created_at.desc())
        )
        return list((await self._session.scalars(stmt)).all())
