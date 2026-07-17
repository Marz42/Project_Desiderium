"""Embedding provider protocol."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class EmbeddingResult:
    vector: list[float]
    embedding_space: str
    provider: str
    degraded: bool = False
    degradation_reason: str | None = None


class EmbeddingProvider(Protocol):
    embedding_space: str
    provider_name: str

    async def embed(self, text: str) -> EmbeddingResult: ...

    async def close(self) -> None: ...
