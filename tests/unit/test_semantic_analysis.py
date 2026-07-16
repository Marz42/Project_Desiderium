"""Unit tests for semantic analysis helpers."""

from __future__ import annotations

from app.services.semantic_analysis import SemanticAnalysisService


def test_metadata_fallback_summary() -> None:
    payload = [
        {"title_original": "JJK Gojo fight", "title_zh": "咒术回战五条悟战斗"},
        {"title_original": "Sukuna battle explained"},
    ]
    summary = SemanticAnalysisService._metadata_fallback_summary(payload)
    assert "咒术回战" in summary or "JJK" in summary
    assert "低置信度" in summary


def test_parse_format() -> None:
    from app.models import CreativeFormat

    assert SemanticAnalysisService._parse_format("short") == CreativeFormat.SHORT
    assert SemanticAnalysisService._parse_format("long") == CreativeFormat.LONG
    assert SemanticAnalysisService._parse_format("both") == CreativeFormat.BOTH
