"""Rule-based trend clustering using anime entity dictionary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.trend_metrics import normalize_title
from app.models import TopicType
from app.services.scoring_config import (
    EntityDictionary,
    EntityRule,
    get_entity_dictionary,
    get_scoring_config,
)


@dataclass(frozen=True)
class EntityMatch:
    entity: EntityRule
    keywords_matched: tuple[str, ...]
    hit_count: int
    membership_score: float


@dataclass(frozen=True)
class VideoClusterAssignment:
    content_item_id: str
    entity_id: str
    canonical_name: str
    anime_title: str
    topic_type: str
    membership_score: float
    evidence: dict[str, Any]


def match_entity(title: str, dictionary: EntityDictionary | None = None) -> EntityMatch | None:
    dictionary = dictionary or get_entity_dictionary()
    normalized = normalize_title(title)
    best: EntityMatch | None = None

    for entity in dictionary.entities:
        matched = tuple(kw for kw in entity.keywords if kw in normalized)
        if not matched:
            continue
        hit_count = len(matched)
        score = min(1.0, 0.5 + 0.1 * hit_count)
        candidate = EntityMatch(
            entity=entity,
            keywords_matched=matched,
            hit_count=hit_count,
            membership_score=score,
        )
        if best is None or candidate.hit_count > best.hit_count:
            best = candidate

    return best


def topic_type_from_string(value: str) -> TopicType:
    mapping = {
        "anime": TopicType.ANIME,
        "character": TopicType.CHARACTER,
        "arc": TopicType.ARC,
        "event": TopicType.EVENT,
        "selling_point": TopicType.SELLING_POINT,
    }
    return mapping.get(value, TopicType.ANIME)


def cluster_videos(
    videos: list[dict[str, Any]],
    *,
    dictionary: EntityDictionary | None = None,
) -> dict[str, list[VideoClusterAssignment]]:
    """Group videos by best entity match. Unmatched videos are excluded."""
    dictionary = dictionary or get_entity_dictionary()
    clusters: dict[str, list[VideoClusterAssignment]] = {}

    for video in videos:
        title = video.get("title") or video.get("title_original") or ""
        match = match_entity(title, dictionary)
        if match is None:
            continue
        entity = match.entity
        assignment = VideoClusterAssignment(
            content_item_id=str(video["content_item_id"]),
            entity_id=entity.entity_id,
            canonical_name=entity.canonical_name,
            anime_title=entity.anime_title,
            topic_type=entity.topic_type,
            membership_score=match.membership_score,
            evidence={
                "keywords_matched": list(match.keywords_matched),
                "title": title,
            },
        )
        clusters.setdefault(entity.entity_id, []).append(assignment)

    cfg = get_scoring_config()
    filtered: dict[str, list[VideoClusterAssignment]] = {}
    video_by_id = {str(video["content_item_id"]): video for video in videos}

    for entity_id, members in clusters.items():
        channel_ids = {
            video_by_id[m.content_item_id].get("channel_id")
            or video_by_id[m.content_item_id].get("channel_external_id")
            for m in members
            if m.content_item_id in video_by_id
        }
        unique_channels = {cid for cid in channel_ids if cid}
        if len(members) < cfg.thresholds.min_cluster_members:
            continue
        if len(unique_channels) < cfg.thresholds.min_cluster_channels:
            continue
        filtered[entity_id] = members

    return filtered


def assignments_to_member_rows(
    assignments: list[VideoClusterAssignment],
    video_lookup: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for assignment in assignments:
        video = video_lookup.get(assignment.content_item_id, {})
        rows.append(
            {
                "content_item_id": assignment.content_item_id,
                "membership_score": assignment.membership_score,
                "evidence": assignment.evidence,
                "channel_id": video.get("channel_id") or video.get("channel_external_id"),
                "tier": video.get("tier", "general"),
                "capped_breakout": video.get("capped_breakout", 1.0),
                "breakout_ratio": video.get("breakout_ratio", 1.0),
                "views": video.get("views", 0),
                "incremental_views": video.get("incremental_views", 0),
                "published_at": video.get("published_at"),
                "relevance_category": video.get("relevance_category"),
                "relevance_multiplier": video.get("relevance_multiplier", 1.0),
                "language": video.get("language"),
                "title": video.get("title") or video.get("title_original"),
            }
        )
    return rows
