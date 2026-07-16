"""Semantic similarity deduplication for creative angles."""

from __future__ import annotations

import hashlib
import re
import unicodedata

from app.models import CreativeAngle

_TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)


def normalize_angle_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).lower().strip()
    return re.sub(r"\s+", " ", normalized)


def tokenize_angle(text: str) -> set[str]:
    normalized = normalize_angle_text(text)
    latin = set(_TOKEN_RE.findall(normalized))
    cjk = {ch for ch in normalized if "\u4e00" <= ch <= "\u9fff"}
    return latin | cjk


def semantic_fingerprint(text: str) -> str:
    tokens = sorted(tokenize_angle(text))
    payload = "|".join(tokens)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def jaccard_similarity(a: str, b: str) -> float:
    tokens_a = tokenize_angle(a)
    tokens_b = tokenize_angle(b)
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


def is_semantic_duplicate(
    angle_zh: str,
    existing: list[CreativeAngle],
    *,
    threshold: float = 0.72,
) -> bool:
    fingerprint = semantic_fingerprint(angle_zh)
    for item in existing:
        if item.semantic_fingerprint and item.semantic_fingerprint == fingerprint:
            return True
        if jaccard_similarity(angle_zh, item.angle_zh) >= threshold:
            return True
    return False


def _as_dedup_entries(existing: list[CreativeAngle]) -> list[tuple[str, str | None]]:
    return [(item.angle_zh, item.semantic_fingerprint) for item in existing]


def _is_duplicate_against(
    angle_zh: str,
    entries: list[tuple[str, str | None]],
    *,
    threshold: float,
) -> bool:
    fingerprint = semantic_fingerprint(angle_zh)
    for text, stored_fp in entries:
        if stored_fp and stored_fp == fingerprint:
            return True
        if jaccard_similarity(angle_zh, text) >= threshold:
            return True
    return False


def filter_unique_angles(
    angles: list[dict],
    existing: list[CreativeAngle],
    *,
    threshold: float = 0.72,
) -> list[dict]:
    """Filter proposed angles against historical ones; also dedupe within batch."""
    accepted: list[dict] = []
    seen = _as_dedup_entries(existing)
    for angle in angles:
        text = str(angle.get("angle_zh") or "")
        if not text:
            continue
        if _is_duplicate_against(text, seen, threshold=threshold):
            continue
        accepted.append(angle)
        seen.append((text, semantic_fingerprint(text)))
    return accepted
