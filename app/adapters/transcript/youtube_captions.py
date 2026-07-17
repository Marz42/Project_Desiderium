"""Fetch public YouTube captions without the official captions.list API."""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

WATCH_PAGE_RE = re.compile(r'"captionTracks":(\[.*?\])')
INNERTUBE_RE = re.compile(r'"INNERTUBE_API_KEY":"([^"]+)"')


@dataclass(frozen=True)
class CaptionFetchResult:
    text: str
    language: str
    source: str = "public_caption"
    confidence: float = 0.85


class YouTubeCaptionsFetcher:
    """Extract auto-generated or uploaded captions from the public watch page."""

    def __init__(self, *, timeout: float = 30.0) -> None:
        self._timeout = timeout

    async def close(self) -> None:
        return None

    async def fetch(
        self,
        video_external_id: str,
        *,
        preferred_languages: tuple[str, ...] = ("en", "en-US", "en-GB"),
    ) -> CaptionFetchResult | None:
        return await asyncio.to_thread(
            self._fetch_sync,
            video_external_id,
            preferred_languages,
        )

    def _fetch_sync(
        self,
        video_external_id: str,
        preferred_languages: tuple[str, ...],
    ) -> CaptionFetchResult | None:
        watch_url = f"https://www.youtube.com/watch?v={video_external_id}"
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; DesideriumBot/1.0; +https://localhost)",
            "Accept-Language": "en-US,en;q=0.9",
        }
        try:
            with httpx.Client(
                timeout=self._timeout, headers=headers, follow_redirects=True
            ) as client:
                response = client.get(watch_url)
                response.raise_for_status()
                html = response.text

                tracks = self._parse_caption_tracks(html)
                if not tracks:
                    return None

                track = self._select_track(tracks, preferred_languages)
                if track is None:
                    return None

                base_url = track.get("baseUrl")
                if not isinstance(base_url, str) or not base_url:
                    return None

                language = str(track.get("languageCode") or "en")
                caption_response = client.get(base_url)
                caption_response.raise_for_status()
                text = self._parse_vtt_or_xml(caption_response.text)
        except httpx.HTTPError as exc:
            logger.debug("caption fetch failed: %s", exc)
            return None

        if not text.strip():
            return None
        return CaptionFetchResult(text=text.strip(), language=language)

    @staticmethod
    def _parse_caption_tracks(html: str) -> list[dict]:
        match = WATCH_PAGE_RE.search(html)
        if not match:
            return []
        import json

        try:
            tracks = json.loads(match.group(1))
        except json.JSONDecodeError:
            return []
        if not isinstance(tracks, list):
            return []
        return [t for t in tracks if isinstance(t, dict)]

    @staticmethod
    def _select_track(
        tracks: list[dict],
        preferred_languages: tuple[str, ...],
    ) -> dict | None:
        for lang in preferred_languages:
            for track in tracks:
                if track.get("languageCode") == lang:
                    return track
        for track in tracks:
            code = str(track.get("languageCode") or "")
            if code.startswith("en"):
                return track
        return tracks[0] if tracks else None

    @staticmethod
    def _parse_vtt_or_xml(raw: str) -> str:
        lines: list[str] = []
        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("WEBVTT"):
                continue
            if "-->" in stripped:
                continue
            if stripped.isdigit():
                continue
            if stripped.startswith("<"):
                stripped = re.sub(r"<[^>]+>", "", stripped)
            if stripped:
                lines.append(stripped)
        return " ".join(lines)
