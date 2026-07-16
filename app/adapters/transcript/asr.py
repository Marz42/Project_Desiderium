"""Optional ASR adapter interface for speech-to-text fallback."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class AsrResult:
    text: str
    language: str | None
    confidence: float | None


class AsrAdapter(ABC):
    """Platform-agnostic automatic speech recognition interface."""

    @abstractmethod
    async def transcribe(
        self,
        *,
        video_external_id: str,
        video_url: str | None,
        language_hint: str | None = None,
    ) -> AsrResult | None:
        """Return transcript text or None when ASR is unavailable."""


class NullAsrAdapter(AsrAdapter):
    """No-op ASR — always returns None (metadata-only fallback)."""

    async def transcribe(
        self,
        *,
        video_external_id: str,
        video_url: str | None,
        language_hint: str | None = None,
    ) -> AsrResult | None:
        return None
