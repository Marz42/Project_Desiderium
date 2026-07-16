"""Creative angle repository."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
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
    ) -> CreativeAngle:
        angle = CreativeAngle(
            trend_id=trend_id,
            angle_zh=angle_zh,
            format=format,
            evidence_content_ids=evidence_content_ids,
            generated_date=generated_date,
            generation_source=generation_source,
            semantic_fingerprint=semantic_fingerprint,
            status=AngleStatus.CANDIDATE,
        )
        self._session.add(angle)
        await self._session.flush()
        return angle
