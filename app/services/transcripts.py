"""Transcript acquisition service with state machine and metadata fallback."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters.transcript.asr import AsrAdapter, NullAsrAdapter
from app.adapters.transcript.youtube_captions import YouTubeCaptionsFetcher
from app.models import (
    ContentItem,
    Platform,
    TranscriptSource,
    TranscriptStatus,
    WatchItem,
    WatchTier,
)
from app.repositories.transcripts import TranscriptRepository
from app.services.llm_config import LlmConfig, get_llm_config

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TranscriptExcerpt:
    content_item_id: str
    source: str
    text: str
    confidence: float
    has_captions: bool


class TranscriptService:
    """State machine: pending → success | failed | unavailable."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        captions_fetcher: YouTubeCaptionsFetcher | None = None,
        asr_adapter: AsrAdapter | None = None,
        config: LlmConfig | None = None,
    ) -> None:
        self._session = session
        self._repo = TranscriptRepository(session)
        self._captions = captions_fetcher or YouTubeCaptionsFetcher()
        self._asr = asr_adapter or NullAsrAdapter()
        self._config = config or get_llm_config()
        self._summary_cache: dict[str, tuple[datetime, str]] = {}

    async def close(self) -> None:
        await self._captions.close()

    async def fetch_for_priority_candidates(self, *, limit: int = 50) -> dict[str, Any]:
        items = await self._load_priority_candidates(limit=limit)
        processed = 0
        success = 0
        unavailable = 0
        failed = 0

        for item in items:
            outcome = await self.fetch_for_content(item)
            processed += 1
            if outcome == TranscriptStatus.SUCCESS:
                success += 1
            elif outcome == TranscriptStatus.UNAVAILABLE:
                unavailable += 1
            elif outcome == TranscriptStatus.FAILED:
                failed += 1

        await self._session.commit()
        return {
            "processed": processed,
            "success": success,
            "unavailable": unavailable,
            "failed": failed,
        }

    async def fetch_for_content(self, item: ContentItem) -> TranscriptStatus:
        pending = await self._repo.upsert_pending(item.id, TranscriptSource.PUBLIC_CAPTION)

        if item.platform != Platform.YOUTUBE:
            await self._repo.mark_unavailable(
                pending.id, error="platform does not support public captions"
            )
            return TranscriptStatus.UNAVAILABLE

        try:
            caption = await self._captions.fetch(
                item.external_id,
                preferred_languages=self._config.transcripts.preferred_languages,
            )
        except Exception as exc:
            logger.warning("caption fetch error for %s: %s", item.external_id, exc)
            await self._repo.mark_failed(pending.id, error=str(exc))
            return TranscriptStatus.FAILED

        if caption is not None:
            text = self._truncate_text(caption.text)
            await self._repo.mark_success(
                pending.id,
                text=text,
                language=caption.language,
                confidence=caption.confidence,
            )
            return TranscriptStatus.SUCCESS

        asr_result = await self._asr.transcribe(
            video_external_id=item.external_id,
            video_url=item.url,
            language_hint=item.language,
        )
        if asr_result is not None and asr_result.text.strip():
            asr_pending = await self._repo.upsert_pending(item.id, TranscriptSource.API_ASR)
            await self._repo.mark_success(
                asr_pending.id,
                text=self._truncate_text(asr_result.text),
                language=asr_result.language,
                confidence=asr_result.confidence,
            )
            await self._repo.mark_unavailable(
                pending.id, error="public captions unavailable; used ASR"
            )
            return TranscriptStatus.SUCCESS

        await self._repo.mark_unavailable(
            pending.id, error="no public captions; metadata-only fallback"
        )
        return TranscriptStatus.UNAVAILABLE

    def build_excerpt(self, item: ContentItem, transcript_text: str | None) -> TranscriptExcerpt:
        if transcript_text and transcript_text.strip():
            excerpt = self._cached_excerpt(item.id, transcript_text)
            return TranscriptExcerpt(
                content_item_id=str(item.id),
                source="transcript",
                text=excerpt,
                confidence=0.85,
                has_captions=True,
            )
        metadata = self._metadata_only_text(item)
        return TranscriptExcerpt(
            content_item_id=str(item.id),
            source="metadata",
            text=metadata,
            confidence=0.35,
            has_captions=False,
        )

    def _cached_excerpt(self, content_id: uuid.UUID, full_text: str) -> str:
        cache_key = str(content_id)
        now = datetime.now(UTC)
        ttl = self._config.transcripts.summary_cache_ttl_seconds
        cached = self._summary_cache.get(cache_key)
        if cached and (now - cached[0]).total_seconds() < ttl:
            return cached[1]

        max_chars = self._config.transcripts.excerpt_chars
        excerpt = full_text[:max_chars]
        if len(full_text) > max_chars:
            excerpt += "…"
        self._summary_cache[cache_key] = (now, excerpt)
        return excerpt

    def _truncate_text(self, text: str) -> str:
        max_chars = self._config.transcripts.max_text_chars
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "…"

    @staticmethod
    def _metadata_only_text(item: ContentItem) -> str:
        parts = [item.title_original]
        if item.description:
            parts.append(item.description[:500])
        if item.tags:
            parts.append("Tags: " + ", ".join(str(t) for t in item.tags[:10]))
        if item.duration_seconds:
            parts.append(f"Duration: {item.duration_seconds}s")
        return "\n".join(parts)

    async def _load_priority_candidates(self, *, limit: int) -> list[ContentItem]:
        stmt = (
            select(ContentItem)
            .join(
                WatchItem,
                (WatchItem.external_id == ContentItem.channel_external_id)
                & (WatchItem.platform == ContentItem.platform),
            )
            .options(selectinload(ContentItem.transcripts))
            .where(
                ContentItem.platform == Platform.YOUTUBE,
                WatchItem.tier == WatchTier.PRIORITY,
                WatchItem.enabled.is_(True),
            )
            .order_by(ContentItem.published_at.desc().nullslast())
            .limit(limit)
        )
        items = list((await self._session.scalars(stmt)).all())
        due: list[ContentItem] = []
        for item in items:
            if self._needs_fetch(item):
                due.append(item)
        return due

    def _needs_fetch(self, item: ContentItem) -> bool:
        if not item.transcripts:
            return True
        if any(t.status == TranscriptStatus.SUCCESS for t in item.transcripts):
            return False
        for transcript in item.transcripts:
            if transcript.status in {TranscriptStatus.PENDING, TranscriptStatus.FAILED}:
                return True
            if transcript.status == TranscriptStatus.UNAVAILABLE:
                retry_after = transcript.updated_at + timedelta(
                    days=self._config.transcripts.unavailable_retry_days,
                )
                if datetime.now(UTC) >= retry_after:
                    return True
        return False
