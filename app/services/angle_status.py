"""Angle status state machine with audit trail."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AngleStatus, AngleStatusAudit, CreativeAngle, PublicationRecord, PublicationStatus


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
    ) -> CreativeAngle:
        from_status = angle.status
        if from_status != to_status and not self.can_transition(from_status, to_status):
            raise InvalidStatusTransition(from_status, to_status)

        if from_status == to_status:
            return angle

        angle.status = to_status
        self._session.add(
            AngleStatusAudit(
                creative_angle_id=angle.id,
                from_status=from_status,
                to_status=to_status,
                note=note,
            ),
        )
        await self._record_publication(angle, to_status, note=note, published_url=published_url)
        await self._session.flush()
        return angle

    async def _record_publication(
        self,
        angle: CreativeAngle,
        status: AngleStatus,
        *,
        note: str | None,
        published_url: str | None,
    ) -> None:
        pub_map = {
            AngleStatus.ADOPTED: PublicationStatus.ADOPTED,
            AngleStatus.PUBLISHED: PublicationStatus.PUBLISHED,
            AngleStatus.REUSABLE: PublicationStatus.REUSABLE,
            AngleStatus.BLOCKED: PublicationStatus.BLOCKED,
        }
        pub_status = pub_map.get(status)
        if pub_status is None:
            return

        record = PublicationRecord(
            creative_angle_id=angle.id,
            status=pub_status,
            published_url=published_url,
            published_at=datetime.now(UTC) if status == AngleStatus.PUBLISHED else None,
            note=note,
        )
        self._session.add(record)

    async def list_audits(self, angle_id: uuid.UUID) -> list[AngleStatusAudit]:
        stmt = (
            select(AngleStatusAudit)
            .where(AngleStatusAudit.creative_angle_id == angle_id)
            .order_by(AngleStatusAudit.created_at.desc())
        )
        return list((await self._session.scalars(stmt)).all())
