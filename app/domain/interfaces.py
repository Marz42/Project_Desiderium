from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class SourceAdapter(ABC):
    """Platform-agnostic interface for discovering and ingesting external content."""

    @abstractmethod
    async def discover_items(
        self,
        watch_item: dict[str, Any],
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """Discover new content items for a watchlist entry."""

    @abstractmethod
    async def fetch_item_details(self, external_ids: list[str]) -> list[dict[str, Any]]:
        """Fetch metadata for one or more platform content IDs."""

    @abstractmethod
    async def fetch_metrics(self, external_ids: list[str]) -> list[dict[str, Any]]:
        """Fetch current engagement metrics for content IDs."""

    @abstractmethod
    def normalize_item(self, raw_item: dict[str, Any]) -> dict[str, Any]:
        """Map a platform-specific payload into the canonical content schema."""

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Report adapter availability and credential validity."""


class TranscriptAdapter(ABC):
    """Platform-agnostic interface for fetching video transcripts and captions."""

    @abstractmethod
    async def discover_items(
        self,
        watch_item: dict[str, Any],
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """Discover transcript candidates linked to watchlist-driven content."""

    @abstractmethod
    async def fetch_item_details(self, external_ids: list[str]) -> list[dict[str, Any]]:
        """Fetch transcript metadata (language, source, availability)."""

    @abstractmethod
    async def fetch_metrics(self, external_ids: list[str]) -> list[dict[str, Any]]:
        """Fetch transcript processing status and quality signals."""

    @abstractmethod
    def normalize_item(self, raw_item: dict[str, Any]) -> dict[str, Any]:
        """Map a platform-specific transcript payload into the canonical schema."""

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Report transcript provider availability."""
