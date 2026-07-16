"""Unit tests for creative angle semantic deduplication."""

from __future__ import annotations

from datetime import date

from app.models import AngleStatus, CreativeAngle, CreativeFormat, GenerationSource
from app.services.angle_dedup import (
    filter_unique_angles,
    is_semantic_duplicate,
    jaccard_similarity,
    semantic_fingerprint,
)


def _angle(text: str) -> CreativeAngle:
    return CreativeAngle(
        trend_id=None,  # type: ignore[arg-type]
        angle_zh=text,
        format=CreativeFormat.SHORT,
        evidence_content_ids=["id-1"],
        generated_date=date.today(),
        generation_source=GenerationSource.LLM,
        semantic_fingerprint=semantic_fingerprint(text),
        status=AngleStatus.CANDIDATE,
    )


def test_jaccard_similarity_high_for_rephrase() -> None:
    a = "你可能忽略的三个角色细节"
    b = "三个你可能忽略的角色细节"
    assert jaccard_similarity(a, b) >= 0.7


def test_is_semantic_duplicate_by_fingerprint() -> None:
    text = "角色为什么背叛主角"
    existing = [_angle(text)]
    assert is_semantic_duplicate(text, existing)


def test_filter_unique_angles_dedupes_batch() -> None:
    existing = [_angle("最残酷的一场战斗解析")]
    proposed = [
        {"angle_zh": "最残酷的一场战斗解析", "format": "short", "evidence_content_ids": ["1"]},
        {"angle_zh": "这个角色真正的结局", "format": "long", "evidence_content_ids": ["2"]},
    ]
    unique = filter_unique_angles(proposed, existing, threshold=0.72)
    assert len(unique) == 1
    assert unique[0]["angle_zh"] == "这个角色真正的结局"
