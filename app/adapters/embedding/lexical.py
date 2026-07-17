"""Deterministic lexical embedding used as safe fallback."""

from __future__ import annotations

import hashlib
import math
import re

from app.adapters.embedding.base import EmbeddingResult

_TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)
LEXICAL_SPACE = "lexical:char-ngram-v1"
DIM = 256


class LexicalEmbeddingProvider:
    provider_name = "lexical"
    embedding_space = LEXICAL_SPACE

    def __init__(self, *, degraded: bool = False, reason: str | None = None) -> None:
        self._degraded = degraded
        self._reason = reason

    async def embed(self, text: str) -> EmbeddingResult:
        tokens = _TOKEN_RE.findall(text.lower())
        grams: list[str] = []
        for token in tokens:
            padded = f"#{token}#"
            grams.extend(padded[i : i + 3] for i in range(max(len(padded) - 2, 1)))
        vector = [0.0] * DIM
        for gram in grams:
            digest = hashlib.sha256(gram.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:2], "big") % DIM
            sign = 1.0 if digest[2] % 2 == 0 else -1.0
            vector[idx] += sign
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return EmbeddingResult(
            vector=[v / norm for v in vector],
            embedding_space=self.embedding_space,
            provider=self.provider_name,
            degraded=self._degraded,
            degradation_reason=self._reason,
        )

    async def close(self) -> None:
        return None
