"""LLM semantic analysis pipeline for trends and creative angles."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters.llm.adapter import LlmAdapter, LlmAdapterError
from app.adapters.llm.client import OpenAICompatibleClient
from app.config import get_settings
from app.models import ContentItem, CreativeFormat, LifecycleStatus, TrendMember, TrendTheme
from app.repositories.content import ContentRepository
from app.repositories.creative_angles import CreativeAngleRepository
from app.repositories.transcripts import TranscriptRepository
from app.repositories.trends import TrendsRepository
from app.schemas.semantic import (
    CreativeAngleItem,
    CreativeAnglesResult,
    TitleTranslationItem,
    TitleTranslationResult,
    TrendNamingResult,
    WhyTrendingResult,
)
from app.services.angle_dedup import filter_unique_angles, semantic_fingerprint
from app.services.evidence import require_evidence_ids, validate_evidence_ids
from app.services.llm_config import LlmConfig, LlmSettings, get_llm_config, load_prompt_template
from app.services.transcripts import TranscriptService

logger = logging.getLogger(__name__)


class SemanticAnalysisService:
    """Translate titles, name trends, summarize why-trending, generate creative angles."""

    def __init__(
        self,
        session: AsyncSession,
        llm: LlmAdapter,
        *,
        transcript_service: TranscriptService | None = None,
        config: LlmConfig | None = None,
    ) -> None:
        self._session = session
        self._llm = llm
        self._config = config or get_llm_config()
        self._transcripts = transcript_service or TranscriptService(session, config=self._config)
        self._trends = TrendsRepository(session)
        self._angles = CreativeAngleRepository(session)
        self._content = ContentRepository(session)
        self._transcript_repo = TranscriptRepository(session)

    async def close(self) -> None:
        await self._transcripts.close()
        await self._llm.close()

    async def run_daily_semantic_analysis(
        self,
        *,
        analysis_date: date | None = None,
        max_trends: int = 30,
    ) -> dict[str, Any]:
        analysis_date = analysis_date or datetime.now(UTC).date()
        trends = await self._load_scored_trends(limit=max_trends)

        analyzed = 0
        angles_created = 0
        llm_failures = 0
        low_confidence = 0

        for trend in trends:
            try:
                result = await self.analyze_trend(trend, analysis_date=analysis_date)
                analyzed += 1
                angles_created += int(result.get("angles_created", 0))
                if result.get("low_confidence"):
                    low_confidence += 1
            except LlmAdapterError as exc:
                llm_failures += 1
                logger.warning(
                    "semantic analysis skipped for trend %s: %s",
                    trend.id,
                    exc,
                )
            except Exception as exc:
                llm_failures += 1
                logger.exception("semantic analysis error for trend %s: %s", trend.id, exc)

        await self._session.commit()
        return {
            "analysis_date": analysis_date.isoformat(),
            "trends_attempted": len(trends),
            "trends_analyzed": analyzed,
            "angles_created": angles_created,
            "llm_failures": llm_failures,
            "low_confidence_trends": low_confidence,
            "llm_usage": self._llm.usage.model_dump(),
        }

    async def analyze_trend(
        self,
        trend: TrendTheme,
        *,
        analysis_date: date,
    ) -> dict[str, Any]:
        members = await self._load_members(trend.id)
        if not members:
            return {"angles_created": 0, "low_confidence": True}

        content_items = [m.content_item for m in members if m.content_item is not None]
        allowed_ids = {str(item.id) for item in content_items}
        evidence_payload = await self._build_evidence_payload(content_items)
        has_captions = any(e.get("has_captions") for e in evidence_payload)
        low_confidence = not has_captions

        await self._translate_titles(content_items, allowed_ids)

        naming = await self._name_trend(trend, evidence_payload, allowed_ids)
        why = await self._summarize_why_trending(
            trend,
            naming.trend_name_zh,
            evidence_payload,
            allowed_ids,
        )

        existing_angles = await self._angles.list_recent_for_dedup(trend_id=trend.id, days=30)
        existing_angles.extend(await self._angles.list_blocked_and_published())

        angles_result = await self._generate_angles(
            trend,
            naming.trend_name_zh,
            why.why_trending_zh,
            evidence_payload,
            allowed_ids,
            existing_angles,
        )

        angles_created = await self._persist_angles(
            trend=trend,
            naming=naming,
            why=why,
            angles=angles_result.creative_angles,
            allowed_ids=allowed_ids,
            existing_angles=existing_angles,
            analysis_date=analysis_date,
        )

        trend.summary_zh = why.why_trending_zh
        if naming.trend_name_zh and naming.confidence >= self._config.semantic.low_confidence_threshold:
            trend.canonical_name = naming.trend_name_zh
        trend.updated_at = datetime.now(UTC)

        return {
            "angles_created": angles_created,
            "low_confidence": low_confidence or naming.confidence < self._config.semantic.low_confidence_threshold,
            "has_captions": has_captions,
        }

    async def _translate_titles(
        self,
        items: list[ContentItem],
        allowed_ids: set[str],
    ) -> None:
        pending = [item for item in items if not item.title_zh and str(item.id) in allowed_ids]
        if not pending:
            return

        titles_json = [
            {"content_id": str(item.id), "title_original": item.title_original}
            for item in pending[: self._config.semantic.max_evidence_videos_per_request]
        ]
        prompt = load_prompt_template("title_translation")
        try:
            result = await self._llm.complete_structured(
                prompt,
                {"titles_json": titles_json},
                TitleTranslationResult,
            )
        except LlmAdapterError:
            return

        by_id = {str(item.id): item for item in pending}
        for translation in result.translations:
            if translation.content_id not in allowed_ids:
                continue
            item = by_id.get(translation.content_id)
            if item is not None and translation.title_zh.strip():
                item.title_zh = translation.title_zh.strip()

    async def _name_trend(
        self,
        trend: TrendTheme,
        evidence_payload: list[dict[str, Any]],
        allowed_ids: set[str],
    ) -> TrendNamingResult:
        prompt = load_prompt_template("trend_naming")
        try:
            result = await self._llm.complete_structured(
                prompt,
                {
                    "canonical_name": trend.canonical_name,
                    "anime_title": trend.anime_title or "",
                    "entities_json": trend.entities or {},
                    "evidence_videos_json": evidence_payload,
                },
                TrendNamingResult,
            )
            result.evidence_content_ids = require_evidence_ids(
                result.evidence_content_ids,
                allowed_ids,
            )
            return result
        except (LlmAdapterError, ValueError):
            return TrendNamingResult(
                trend_name_zh=trend.canonical_name,
                evidence_content_ids=list(allowed_ids)[:1],
                confidence=0.3,
            )

    async def _summarize_why_trending(
        self,
        trend: TrendTheme,
        trend_name_zh: str,
        evidence_payload: list[dict[str, Any]],
        allowed_ids: set[str],
    ) -> WhyTrendingResult:
        metrics_context = {
            "lifecycle_status": trend.lifecycle_status.value if trend.lifecycle_status else None,
            "score": trend.score,
            "score_components": trend.score_components or {},
            "note": "Precomputed by deterministic scoring — do not recalculate.",
        }
        prompt = load_prompt_template("why_trending")
        try:
            result = await self._llm.complete_structured(
                prompt,
                {
                    "trend_name_zh": trend_name_zh,
                    "anime_title": trend.anime_title or "",
                    "metrics_context_json": metrics_context,
                    "evidence_videos_json": evidence_payload,
                },
                WhyTrendingResult,
            )
            result.evidence_content_ids = require_evidence_ids(
                result.evidence_content_ids,
                allowed_ids,
            )
            return result
        except (LlmAdapterError, ValueError):
            fallback = self._metadata_fallback_summary(evidence_payload)
            return WhyTrendingResult(
                why_trending_zh=fallback,
                evidence_content_ids=list(allowed_ids)[: min(3, len(allowed_ids))],
                confidence=0.25,
            )

    async def _generate_angles(
        self,
        trend: TrendTheme,
        trend_name_zh: str,
        why_trending_zh: str,
        evidence_payload: list[dict[str, Any]],
        allowed_ids: set[str],
        existing_angles: list,
    ) -> CreativeAnglesResult:
        existing_json = [
            {"angle_zh": a.angle_zh, "format": a.format.value, "status": a.status.value}
            for a in existing_angles[:20]
        ]
        semantic = self._config.semantic
        prompt = load_prompt_template("creative_angles")
        try:
            result = await self._llm.complete_structured(
                prompt,
                {
                    "trend_name_zh": trend_name_zh,
                    "why_trending_zh": why_trending_zh,
                    "anime_title": trend.anime_title or "",
                    "evidence_videos_json": evidence_payload,
                    "existing_angles_json": existing_json,
                    "min_angles": semantic.min_angles_per_trend,
                    "max_angles": semantic.max_angles_per_trend,
                },
                CreativeAnglesResult,
            )
            validated: list[CreativeAngleItem] = []
            for angle in result.creative_angles:
                ids = validate_evidence_ids(angle.evidence_content_ids, allowed_ids)
                if not ids:
                    continue
                angle.evidence_content_ids = ids
                validated.append(angle)
            result.creative_angles = validated[: semantic.max_angles_per_trend]
            return result
        except LlmAdapterError:
            return self._fallback_angles(trend_name_zh, evidence_payload, allowed_ids)

    def _fallback_angles(
        self,
        trend_name_zh: str,
        evidence_payload: list[dict[str, Any]],
        allowed_ids: set[str],
    ) -> CreativeAnglesResult:
        first_id = next(iter(allowed_ids), "")
        title = evidence_payload[0].get("title_zh") or evidence_payload[0].get("title_original", "")
        angle = CreativeAngleItem(
            angle_zh=f"围绕「{trend_name_zh}」解读：{title}",
            format="both",
            evidence_content_ids=[first_id] if first_id else [],
            novelty_reason="metadata-only low-confidence fallback",
        )
        return CreativeAnglesResult(creative_angles=[angle], confidence=0.2)

    async def _persist_angles(
        self,
        *,
        trend: TrendTheme,
        naming: TrendNamingResult,
        why: WhyTrendingResult,
        angles: list[CreativeAngleItem],
        allowed_ids: set[str],
        existing_angles: list,
        analysis_date: date,
    ) -> int:
        raw_angles = [
            {
                "angle_zh": a.angle_zh,
                "format": a.format,
                "evidence_content_ids": a.evidence_content_ids,
            }
            for a in angles
        ]
        unique = filter_unique_angles(
            raw_angles,
            existing_angles,
            threshold=self._config.semantic.dedup_similarity_threshold,
        )

        created = 0
        for item in unique[: self._config.semantic.max_angles_per_trend]:
            ids = validate_evidence_ids(item.get("evidence_content_ids", []), allowed_ids)
            if not ids:
                continue
            fmt = self._parse_format(str(item.get("format") or "both"))
            await self._angles.create_angle(
                trend_id=trend.id,
                angle_zh=str(item["angle_zh"]),
                format=fmt,
                evidence_content_ids=ids,
                generated_date=analysis_date,
                semantic_fingerprint=semantic_fingerprint(str(item["angle_zh"])),
            )
            created += 1
        return created

    async def _build_evidence_payload(
        self,
        items: list[ContentItem],
    ) -> list[dict[str, Any]]:
        ids = [item.id for item in items]
        transcripts = await self._transcript_repo.list_success_for_contents(ids)
        payload: list[dict[str, Any]] = []
        for item in items[: self._config.semantic.max_evidence_videos_per_request]:
            transcript = transcripts.get(item.id)
            excerpt = self._transcripts.build_excerpt(item, transcript.text if transcript else None)
            payload.append(
                {
                    "content_id": str(item.id),
                    "external_id": item.external_id,
                    "title_original": item.title_original,
                    "title_zh": item.title_zh,
                    "channel_name": item.channel_name,
                    "duration_seconds": item.duration_seconds,
                    "description_excerpt": (item.description or "")[:300],
                    "transcript_excerpt": excerpt.text,
                    "has_captions": excerpt.has_captions,
                    "source": excerpt.source,
                },
            )
        return payload

    async def _load_scored_trends(self, *, limit: int) -> list[TrendTheme]:
        stmt = (
            select(TrendTheme)
            .where(
                TrendTheme.lifecycle_status != LifecycleStatus.DORMANT,
                TrendTheme.score.is_not(None),
            )
            .order_by(TrendTheme.score.desc().nullslast())
            .limit(limit)
        )
        return list((await self._session.scalars(stmt)).all())

    async def _load_members(self, trend_id: uuid.UUID) -> list[TrendMember]:
        stmt = (
            select(TrendMember)
            .options(selectinload(TrendMember.content_item))
            .where(TrendMember.trend_id == trend_id)
        )
        return list((await self._session.scalars(stmt)).all())

    @staticmethod
    def _parse_format(value: str) -> CreativeFormat:
        normalized = value.lower().strip()
        if normalized == "short":
            return CreativeFormat.SHORT
        if normalized == "long":
            return CreativeFormat.LONG
        return CreativeFormat.BOTH

    @staticmethod
    def _metadata_fallback_summary(evidence_payload: list[dict[str, Any]]) -> str:
        titles = [
            str(e.get("title_zh") or e.get("title_original") or "")
            for e in evidence_payload[:3]
            if e.get("title_zh") or e.get("title_original")
        ]
        if not titles:
            return "相关视频近期受到关注（仅基于标题与简介，无字幕证据）。"
        joined = "；".join(titles)
        return f"多个相关视频围绕相似题材发布：{joined}（低置信度，仅元数据）。"


async def create_semantic_analysis_service(session: AsyncSession) -> SemanticAnalysisService:
    settings = get_settings()
    config = get_llm_config()
    base_url = settings.llm_base_url or config.llm.base_url
    model = settings.llm_model or config.llm.model
    client = OpenAICompatibleClient(
        api_key=settings.llm_api_key,
        base_url=base_url,
        timeout=config.llm.timeout_seconds,
    )
    merged_config = LlmConfig(
        llm=LlmSettings(
            base_url=base_url,
            model=model,
            timeout_seconds=config.llm.timeout_seconds,
            max_retries=config.llm.max_retries,
            retry_backoff_seconds=config.llm.retry_backoff_seconds,
            temperature=config.llm.temperature,
            max_output_tokens=config.llm.max_output_tokens,
        ),
        transcripts=config.transcripts,
        semantic=config.semantic,
    )
    llm = LlmAdapter(client, merged_config)
    return SemanticAnalysisService(session, llm, config=merged_config)
