"""Creative angle repository."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AngleStatus, CreativeAngle, CreativeFormat, GenerationSource


class CreativeAngleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_trend(self, trend_id: uuid.UUID) -> list[CreativeAngle]:
        stmt = (
            select(CreativeAngle)
            .where(CreativeAngle.trend_id == trend_id)
            .order_by(CreativeAngle.generated_date.desc(), CreativeAngle.created_at.desc())
        )
        return list((await self._session.scalars(stmt)).all())

    async def list_recent_for_dedup(
        self,
        *,
        trend_id: uuid.UUID | None = None,
        days: int = 7,
    ) -> list[CreativeAngle]:
        cutoff = datetime.now(UTC).date() - timedelta(days=days)
        stmt = select(CreativeAngle).where(CreativeAngle.generated_date >= cutoff)
        if trend_id is not None:
            stmt = stmt.where(CreativeAngle.trend_id == trend_id)
        stmt = stmt.order_by(CreativeAngle.created_at.desc())
        return list((await self._session.scalars(stmt)).all())

    async def list_blocked_and_published(self) -> list[CreativeAngle]:
        stmt = select(CreativeAngle).where(
            CreativeAngle.status.in_(
                [AngleStatus.BLOCKED, AngleStatus.PUBLISHED, AngleStatus.ADOPTED],
            ),
        )
        return list((await self._session.scalars(stmt)).all())

    async def get_by_id(self, angle_id: uuid.UUID) -> CreativeAngle | None:
        return await self._session.get(CreativeAngle, angle_id)

    async def update_status(self, angle_id: uuid.UUID, status: AngleStatus) -> CreativeAngle | None:
        angle = await self.get_by_id(angle_id)
        if angle is None:
            return None
        angle.status = status
        await self._session.flush()
        return angle

    async def update_note(self, angle_id: uuid.UUID, note: str | None) -> CreativeAngle | None:
        angle = await self.get_by_id(angle_id)
        if angle is None:
            return None
        angle.manager_note = note
        await self._session.flush()
        return angle

    async def list_for_date(self, generated_date: date) -> list[CreativeAngle]:
        stmt = (
            select(CreativeAngle)
            .where(CreativeAngle.generated_date == generated_date)
            .order_by(CreativeAngle.created_at)
        )
        return list((await self._session.scalars(stmt)).all())

    async def create_angle(
        self,
        *,
        trend_id: uuid.UUID,
        angle_zh: str,
        format: CreativeFormat,
        evidence_content_ids: list[str],
        generated_date: date,
        semantic_fingerprint: str | None,
        generation_source: GenerationSource = GenerationSource.LLM,
    ) -> tuple[CreativeAngle, bool]:
        values = {
            "id": uuid.uuid4(),
            "trend_id": trend_id,
            "angle_zh": angle_zh,
            "format": format,
            "evidence_content_ids": evidence_content_ids,
            "generated_date": generated_date,
            "generation_source": generation_source,
            "semantic_fingerprint": semantic_fingerprint,
            "status": AngleStatus.CANDIDATE,
        }
        stmt = (
            insert(CreativeAngle)
            .values(**values)
            .on_conflict_do_nothing(
                constraint="uq_creative_angles_trend_date_fingerprint",
            )
            .returning(CreativeAngle.id)
        )
        angle_id = (await self._session.execute(stmt)).scalar_one_or_none()
        if angle_id is None:
            existing = await self._session.scalar(
                select(CreativeAngle).where(
                    CreativeAngle.trend_id == trend_id,
                    CreativeAngle.generated_date == generated_date,
                    CreativeAngle.semantic_fingerprint == semantic_fingerprint,
                ),
            )
            assert existing is not None
            return existing, False
        angle = await self._session.get(CreativeAngle, angle_id)
        assert angle is not None
        return angle, True
