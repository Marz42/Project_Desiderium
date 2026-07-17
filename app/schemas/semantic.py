"""Pydantic schemas for LLM semantic analysis I/O."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TitleTranslationItem(BaseModel):
    content_id: str
    title_zh: str


class TitleTranslationResult(BaseModel):
    translations: list[TitleTranslationItem]


class TrendNamingResult(BaseModel):
    trend_name_zh: str
    evidence_content_ids: list[str]
    confidence: float = Field(ge=0.0, le=1.0)


class WhyTrendingResult(BaseModel):
    why_trending_zh: str
    evidence_content_ids: list[str]
    confidence: float = Field(ge=0.0, le=1.0)


CreativeFormatLiteral = Literal["short", "long", "both"]


class CreativeAngleItem(BaseModel):
    angle_zh: str
    format: CreativeFormatLiteral
    evidence_content_ids: list[str]
    novelty_reason: str = ""


class CreativeAnglesResult(BaseModel):
    creative_angles: list[CreativeAngleItem]
    confidence: float = Field(ge=0.0, le=1.0)


class FormatClassificationResult(BaseModel):
    format: CreativeFormatLiteral
    evidence_content_ids: list[str]
    rationale_zh: str


ClusterAction = Literal[
    "merge_same_angle",
    "merge_theme_keep_angles_separate",
    "create_new_theme",
    "needs_review",
]


class ClusterAdjudicationResult(BaseModel):
    action: ClusterAction
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    facet_label: str | None = None


class LlmUsageStats(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    requests: int = 0
    failures: int = 0
