"""Transcript repository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Transcript, TranscriptSource, TranscriptStatus


class TranscriptRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_for_content(
        self,
        content_item_id: uuid.UUID,
        source: TranscriptSource | None = None,
    ) -> Transcript | None:
        stmt = select(Transcript).where(Transcript.content_item_id == content_item_id)
        if source is not None:
            stmt = stmt.where(Transcript.source == source)
        stmt = stmt.order_by(Transcript.updated_at.desc())
        return await self._session.scalar(stmt)

    async def list_success_for_contents(
        self,
        content_item_ids: list[uuid.UUID],
    ) -> dict[uuid.UUID, Transcript]:
        if not content_item_ids:
            return {}
        stmt = select(Transcript).where(
            Transcript.content_item_id.in_(content_item_ids),
            Transcript.status == TranscriptStatus.SUCCESS,
        )
        rows = list((await self._session.scalars(stmt)).all())
        result: dict[uuid.UUID, Transcript] = {}
        for row in rows:
            existing = result.get(row.content_item_id)
            if existing is None or (row.obtained_at or row.updated_at) > (
                existing.obtained_at or existing.updated_at
            ):
                result[row.content_item_id] = row
        return result

    async def has_pending_for_contents(self, content_item_ids: list[uuid.UUID]) -> bool:
        if not content_item_ids:
            return False
        stmt = (
            select(Transcript.id)
            .where(
                Transcript.content_item_id.in_(content_item_ids),
                Transcript.status == TranscriptStatus.PENDING,
            )
            .limit(1)
        )
        return (await self._session.scalar(stmt)) is not None

    async def upsert_pending(
        self,
        content_item_id: uuid.UUID,
        source: TranscriptSource,
    ) -> Transcript:
        now = datetime.now(UTC)
        stmt = (
            insert(Transcript)
            .values(
                id=uuid.uuid4(),
                content_item_id=content_item_id,
                source=source,
                status=TranscriptStatus.PENDING,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_update(
                index_elements=["content_item_id", "source"],
                set_={
                    "status": TranscriptStatus.PENDING,
                    "error": None,
                    "updated_at": now,
                },
                where=Transcript.status != TranscriptStatus.SUCCESS,
            )
            .returning(Transcript.id)
        )
        row_id = (await self._session.execute(stmt)).scalar_one_or_none()
        if row_id is None:
            existing = await self.get_for_content(content_item_id, source)
            assert existing is not None
            return existing
        row = await self._session.get(Transcript, row_id)
        assert row is not None
        return row

    async def mark_success(
        self,
        transcript_id: uuid.UUID,
        *,
        text: str,
        language: str | None,
        confidence: float | None,
    ) -> None:
        row = await self._session.get(Transcript, transcript_id)
        if row is None:
            return
        now = datetime.now(UTC)
        row.text = text
        row.language = language
        row.confidence = confidence
        row.status = TranscriptStatus.SUCCESS
        row.obtained_at = now
        row.error = None
        row.updated_at = now

    async def mark_failed(
        self,
        transcript_id: uuid.UUID,
        *,
        error: str,
    ) -> None:
        row = await self._session.get(Transcript, transcript_id)
        if row is None:
            return
        now = datetime.now(UTC)
        row.status = TranscriptStatus.FAILED
        row.error = error[:2000]
        row.updated_at = now

    async def mark_unavailable(
        self,
        transcript_id: uuid.UUID,
        *,
        error: str | None = None,
    ) -> None:
        row = await self._session.get(Transcript, transcript_id)
        if row is None:
            return
        now = datetime.now(UTC)
        row.status = TranscriptStatus.UNAVAILABLE
        row.error = (error or "no captions or ASR available")[:2000]
        row.updated_at = now
