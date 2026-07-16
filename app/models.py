from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class WatchItemType(str, enum.Enum):
    CHANNEL = "channel"
    ACCOUNT = "account"
    KEYWORD = "keyword"
    ANIME = "anime"
    RANKING = "ranking"


class Platform(str, enum.Enum):
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    OTHER = "other"


class WatchTier(str, enum.Enum):
    PRIORITY = "priority"
    GENERAL = "general"
    EXPERIMENTAL = "experimental"


class CrawlOutcome(str, enum.Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class SourceQuality(str, enum.Enum):
    OFFICIAL_API = "official_api"
    SCRAPED = "scraped"
    ESTIMATED = "estimated"


class TranscriptSource(str, enum.Enum):
    PUBLIC_CAPTION = "public_caption"
    LOCAL_ASR = "local_asr"
    API_ASR = "api_asr"


class TranscriptStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"


class AgeBucket(str, enum.Enum):
    H0_6 = "0-6h"
    H6_24 = "6-24h"
    H24_72 = "24-72h"
    D3_7 = "3-7d"


class BaselineConfidence(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TopicType(str, enum.Enum):
    ANIME = "anime"
    CHARACTER = "character"
    ARC = "arc"
    EVENT = "event"
    SELLING_POINT = "selling_point"


class LifecycleStatus(str, enum.Enum):
    NEW = "new"
    RISING = "rising"
    STABLE = "stable"
    DECLINING = "declining"
    REVIVING = "reviving"
    DORMANT = "dormant"


class MembershipMethod(str, enum.Enum):
    RULE = "rule"
    EMBEDDING = "embedding"
    LLM = "llm"
    MANUAL = "manual"


class CreativeFormat(str, enum.Enum):
    SHORT = "short"
    LONG = "long"
    BOTH = "both"


class AngleStatus(str, enum.Enum):
    CANDIDATE = "candidate"
    SELECTED = "selected"
    ADOPTED = "adopted"
    PUBLISHED = "published"
    REUSABLE = "reusable"
    BLOCKED = "blocked"


class GenerationSource(str, enum.Enum):
    LLM = "llm"
    MANUAL = "manual"


class CrawlJobAdapter(str, enum.Enum):
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    TRANSCRIPT = "transcript"


class CrawlJobType(str, enum.Enum):
    DISCOVER = "discover"
    METRICS = "metrics"
    TRANSCRIPT = "transcript"


class CrawlJobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class BriefStatus(str, enum.Enum):
    DRAFT = "draft"
    FINALIZED = "finalized"
    EXPORTED = "exported"


class PublicationStatus(str, enum.Enum):
    ADOPTED = "adopted"
    PUBLISHED = "published"
    REUSABLE = "reusable"
    BLOCKED = "blocked"


class WatchItem(Base):
    __tablename__ = "watch_items"
    __table_args__ = (
        UniqueConstraint("platform", "type", "external_id", name="uq_watch_items_platform_type_external"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type: Mapped[WatchItemType] = mapped_column(Enum(WatchItemType, name="watch_item_type"), nullable=False)
    platform: Mapped[Platform] = mapped_column(Enum(Platform, name="platform"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    external_id: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    tier: Mapped[WatchTier] = mapped_column(
        Enum(WatchTier, name="watch_tier"),
        nullable=False,
        default=WatchTier.GENERAL,
    )
    tags: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True, default=list)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True, default=dict)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status: Mapped[CrawlOutcome | None] = mapped_column(Enum(CrawlOutcome, name="crawl_outcome"), nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    crawl_jobs: Mapped[list[CrawlJob]] = relationship(back_populates="watch_item")


class ContentItem(Base):
    __tablename__ = "content_items"
    __table_args__ = (
        UniqueConstraint("platform", "external_id", name="uq_content_items_platform_external"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform: Mapped[Platform] = mapped_column(Enum(Platform, name="platform"), nullable=False)
    external_id: Mapped[str] = mapped_column(Text, nullable=False)
    source_watch_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("watch_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    channel_external_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    title_original: Mapped[str] = mapped_column(Text, nullable=False)
    title_zh: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True, default=list)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    region: Mapped[str | None] = mapped_column(String(16), nullable=True)
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    metric_snapshots: Mapped[list[MetricSnapshot]] = relationship(back_populates="content_item")
    transcripts: Mapped[list[Transcript]] = relationship(back_populates="content_item")
    trend_memberships: Mapped[list[TrendMember]] = relationship(back_populates="content_item")


class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "content_item_id",
            "captured_at_bucket",
            name="uq_metric_snapshots_content_bucket",
        ),
        Index("ix_metric_snapshots_captured_at", "captured_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    content_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    captured_at_bucket: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    views: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    likes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    comments: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    shares: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    favorites: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    source_quality: Mapped[SourceQuality] = mapped_column(
        Enum(SourceQuality, name="source_quality"),
        nullable=False,
        default=SourceQuality.OFFICIAL_API,
    )

    content_item: Mapped[ContentItem] = relationship(back_populates="metric_snapshots")


class Transcript(Base):
    __tablename__ = "transcripts"
    __table_args__ = (
        UniqueConstraint("content_item_id", "source", name="uq_transcripts_content_source"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    source: Mapped[TranscriptSource] = mapped_column(Enum(TranscriptSource, name="transcript_source"), nullable=False)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[TranscriptStatus] = mapped_column(
        Enum(TranscriptStatus, name="transcript_status"),
        nullable=False,
        default=TranscriptStatus.PENDING,
    )
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    obtained_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    content_item: Mapped[ContentItem] = relationship(back_populates="transcripts")


class ChannelBaseline(Base):
    __tablename__ = "channel_baselines"
    __table_args__ = (
        UniqueConstraint(
            "channel_external_id",
            "platform",
            "age_bucket",
            name="uq_channel_baselines_channel_platform_bucket",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_external_id: Mapped[str] = mapped_column(Text, nullable=False)
    platform: Mapped[Platform] = mapped_column(Enum(Platform, name="platform"), nullable=False)
    age_bucket: Mapped[AgeBucket] = mapped_column(Enum(AgeBucket, name="age_bucket"), nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    median_velocity: Mapped[float | None] = mapped_column(Float, nullable=True)
    p25_velocity: Mapped[float | None] = mapped_column(Float, nullable=True)
    p75_velocity: Mapped[float | None] = mapped_column(Float, nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    confidence: Mapped[BaselineConfidence] = mapped_column(
        Enum(BaselineConfidence, name="baseline_confidence"),
        nullable=False,
        default=BaselineConfidence.LOW,
    )


class TrendTheme(Base):
    __tablename__ = "trend_themes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canonical_name: Mapped[str] = mapped_column(Text, nullable=False)
    anime_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    topic_type: Mapped[TopicType] = mapped_column(Enum(TopicType, name="topic_type"), nullable=False)
    entities: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True, default=dict)
    first_detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    lifecycle_status: Mapped[LifecycleStatus] = mapped_column(
        Enum(LifecycleStatus, name="lifecycle_status"),
        nullable=False,
        default=LifecycleStatus.NEW,
    )
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_components: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    summary_zh: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    members: Mapped[list[TrendMember]] = relationship(back_populates="trend")
    creative_angles: Mapped[list[CreativeAngle]] = relationship(back_populates="trend")
    daily_candidates: Mapped[list[DailyCandidate]] = relationship(back_populates="trend")
    score_snapshots: Mapped[list[TrendScoreSnapshot]] = relationship(back_populates="trend")


class TrendScoreSnapshot(Base):
    __tablename__ = "trend_score_snapshots"
    __table_args__ = (
        UniqueConstraint("trend_id", "snapshot_date", name="uq_trend_score_snapshots_trend_date"),
        Index("ix_trend_score_snapshots_snapshot_date", "snapshot_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trend_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trend_themes.id", ondelete="CASCADE"),
        nullable=False,
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    score_components: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    lifecycle_status: Mapped[LifecycleStatus] = mapped_column(
        Enum(LifecycleStatus, name="lifecycle_status"),
        nullable=False,
    )
    member_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    channel_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    trend: Mapped[TrendTheme] = relationship(back_populates="score_snapshots")


class TrendMember(Base):
    __tablename__ = "trend_members"
    __table_args__ = (
        UniqueConstraint("trend_id", "content_item_id", name="uq_trend_members_trend_content"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trend_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trend_themes.id", ondelete="CASCADE"),
        nullable=False,
    )
    content_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    membership_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    membership_method: Mapped[MembershipMethod] = mapped_column(
        Enum(MembershipMethod, name="membership_method"),
        nullable=False,
        default=MembershipMethod.RULE,
    )
    evidence: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    trend: Mapped[TrendTheme] = relationship(back_populates="members")
    content_item: Mapped[ContentItem] = relationship(back_populates="trend_memberships")


class CreativeAngle(Base):
    __tablename__ = "creative_angles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trend_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trend_themes.id", ondelete="CASCADE"),
        nullable=False,
    )
    angle_zh: Mapped[str] = mapped_column(Text, nullable=False)
    format: Mapped[CreativeFormat] = mapped_column(Enum(CreativeFormat, name="creative_format"), nullable=False)
    evidence_content_ids: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True, default=list)
    generated_date: Mapped[date] = mapped_column(Date, nullable=False)
    generation_source: Mapped[GenerationSource] = mapped_column(
        Enum(GenerationSource, name="generation_source"),
        nullable=False,
        default=GenerationSource.LLM,
    )
    semantic_fingerprint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[AngleStatus] = mapped_column(
        Enum(AngleStatus, name="angle_status"),
        nullable=False,
        default=AngleStatus.CANDIDATE,
    )
    manager_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    trend: Mapped[TrendTheme] = relationship(back_populates="creative_angles")
    daily_candidates: Mapped[list[DailyCandidate]] = relationship(back_populates="creative_angle")
    brief_items: Mapped[list[BriefItem]] = relationship(back_populates="creative_angle")
    publication_records: Mapped[list[PublicationRecord]] = relationship(back_populates="creative_angle")


class DailyCandidate(Base):
    __tablename__ = "daily_candidates"
    __table_args__ = (
        UniqueConstraint("date", "creative_angle_id", name="uq_daily_candidates_date_angle"),
        Index("ix_daily_candidates_date_rank", "date", "rank"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    creative_angle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("creative_angles.id", ondelete="CASCADE"),
        nullable=False,
    )
    trend_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trend_themes.id", ondelete="CASCADE"),
        nullable=False,
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    candidate_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    creative_angle: Mapped[CreativeAngle] = relationship(back_populates="daily_candidates")
    trend: Mapped[TrendTheme] = relationship(back_populates="daily_candidates")


class Brief(Base):
    __tablename__ = "briefs"
    __table_args__ = (
        UniqueConstraint("brief_date", name="uq_briefs_brief_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brief_date: Mapped[date] = mapped_column(Date, nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[BriefStatus] = mapped_column(
        Enum(BriefStatus, name="brief_status"),
        nullable=False,
        default=BriefStatus.DRAFT,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    items: Mapped[list[BriefItem]] = relationship(back_populates="brief", order_by="BriefItem.position")


class BriefItem(Base):
    __tablename__ = "brief_items"
    __table_args__ = (
        UniqueConstraint("brief_id", "creative_angle_id", name="uq_brief_items_brief_angle"),
        Index("ix_brief_items_brief_position", "brief_id", "position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brief_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("briefs.id", ondelete="CASCADE"),
        nullable=False,
    )
    creative_angle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("creative_angles.id", ondelete="CASCADE"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    manager_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    brief: Mapped[Brief] = relationship(back_populates="items")
    creative_angle: Mapped[CreativeAngle] = relationship(back_populates="brief_items")


class PublicationRecord(Base):
    __tablename__ = "publication_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    creative_angle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("creative_angles.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[PublicationStatus] = mapped_column(
        Enum(PublicationStatus, name="publication_status"),
        nullable=False,
    )
    published_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    creative_angle: Mapped[CreativeAngle] = relationship(back_populates="publication_records")


class CrawlJob(Base):
    __tablename__ = "crawl_jobs"
    __table_args__ = (
        Index("ix_crawl_jobs_status_adapter", "status", "adapter"),
        Index("ix_crawl_jobs_watch_item_id", "watch_item_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    adapter: Mapped[CrawlJobAdapter] = mapped_column(Enum(CrawlJobAdapter, name="crawl_job_adapter"), nullable=False)
    job_type: Mapped[CrawlJobType] = mapped_column(Enum(CrawlJobType, name="crawl_job_type"), nullable=False)
    watch_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("watch_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[CrawlJobStatus] = mapped_column(
        Enum(CrawlJobStatus, name="crawl_job_status"),
        nullable=False,
        default=CrawlJobStatus.QUEUED,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    items_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    watch_item: Mapped[WatchItem | None] = relationship(back_populates="crawl_jobs")
