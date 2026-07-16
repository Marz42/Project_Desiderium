"""Async TikTok web scraper client (experimental, cookie-based)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx

from app.adapters.tiktok.errors import CookieExpiredError, TikTokScrapeError
from app.adapters.tiktok.selectors import (
    extract_cursor,
    extract_embedded_json,
    extract_videos_from_state,
    is_cookie_expired_response,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TikTokPageResult:
    videos: list[dict[str, Any]]
    next_cursor: str | None
    raw_state: dict[str, Any]
    url: str


class TikTokClient:
    """Cookie-authenticated TikTok page fetcher with versioned selectors."""

    def __init__(
        self,
        cookie: str,
        *,
        page_version: str = "v1",
        user_agent: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        if not cookie or not cookie.strip():
            raise CookieExpiredError("TIKTOK_COOKIE is not configured")
        self._cookie = cookie.strip()
        self._page_version = page_version
        self._user_agent = user_agent or (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        self._client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers=self._default_headers(),
        )
        self._cookie_valid = True
        self._last_error: str | None = None

    @property
    def cookie_valid(self) -> bool:
        return self._cookie_valid

    @property
    def last_error(self) -> str | None:
        return self._last_error

    def _default_headers(self) -> dict[str, str]:
        return {
            "User-Agent": self._user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Cookie": self._cookie,
        }

    def _redact_cookie(self, text: str) -> str:
        if not self._cookie:
            return text
        return text.replace(self._cookie, "[REDACTED_COOKIE]")

    async def close(self) -> None:
        await self._client.aclose()

    async def fetch_account_videos(
        self,
        username: str,
        *,
        max_items: int = 15,
        cursor: str | None = None,
    ) -> TikTokPageResult:
        handle = username.lstrip("@")
        url = f"https://www.tiktok.com/@{quote(handle)}"
        if cursor:
            url = f"{url}?cursor={quote(cursor)}"
        return await self._fetch_page(url, max_items=max_items)

    async def fetch_keyword_videos(
        self,
        keyword: str,
        *,
        max_items: int = 15,
        cursor: str | None = None,
    ) -> TikTokPageResult:
        url = f"https://www.tiktok.com/search/video?q={quote(keyword)}"
        if cursor:
            url = f"{url}&cursor={quote(cursor)}"
        return await self._fetch_page(url, max_items=max_items)

    async def fetch_tag_videos(
        self,
        tag: str,
        *,
        max_items: int = 15,
        cursor: str | None = None,
    ) -> TikTokPageResult:
        clean_tag = tag.lstrip("#")
        url = f"https://www.tiktok.com/tag/{quote(clean_tag)}"
        if cursor:
            url = f"{url}?cursor={quote(cursor)}"
        return await self._fetch_page(url, max_items=max_items)

    async def fetch_list_url(
        self,
        list_url: str,
        *,
        max_items: int = 15,
        cursor: str | None = None,
    ) -> TikTokPageResult:
        url = list_url
        if cursor:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}cursor={quote(cursor)}"
        return await self._fetch_page(url, max_items=max_items)

    async def health_check(self) -> dict[str, Any]:
        try:
            result = await self.fetch_account_videos("tiktok", max_items=1)
            return {
                "status": "ok",
                "adapter": "tiktok",
                "cookie_valid": self._cookie_valid,
                "selector_version": self._page_version,
                "sample_count": len(result.videos),
            }
        except CookieExpiredError as exc:
            self._cookie_valid = False
            return {
                "status": "cookie_expired",
                "adapter": "tiktok",
                "cookie_valid": False,
                "selector_version": self._page_version,
                "error": str(exc),
            }
        except Exception as exc:  # noqa: BLE001
            self._last_error = str(exc)
            return {
                "status": "degraded",
                "adapter": "tiktok",
                "cookie_valid": self._cookie_valid,
                "selector_version": self._page_version,
                "error": str(exc),
            }

    async def _fetch_page(self, url: str, *, max_items: int) -> TikTokPageResult:
        try:
            response = await self._client.get(url)
        except httpx.HTTPError as exc:
            self._last_error = str(exc)
            raise TikTokScrapeError(f"HTTP request failed: {exc}") from exc

        body = response.text
        if is_cookie_expired_response(
            status_code=response.status_code,
            url=str(response.url),
            body=body,
            version=self._page_version,
        ):
            self._cookie_valid = False
            logger.warning(
                "TikTok cookie appears expired",
                extra={"service": "tiktok", "component": "client", "url": url},
            )
            raise CookieExpiredError("TikTok session cookie expired or invalid")

        if response.status_code >= 400:
            self._last_error = f"HTTP {response.status_code}"
            raise TikTokScrapeError(f"TikTok returned HTTP {response.status_code}")

        try:
            state = extract_embedded_json(body, version=self._page_version)
        except ValueError as exc:
            safe_body = self._redact_cookie(body[:500])
            logger.error(
                "TikTok page parse failed",
                extra={
                    "service": "tiktok",
                    "component": "client",
                    "url": url,
                    "selector_version": self._page_version,
                    "body_preview": safe_body,
                },
            )
            raise TikTokScrapeError(str(exc)) from exc

        videos = extract_videos_from_state(state)[:max_items]
        next_cursor = extract_cursor(state)
        return TikTokPageResult(
            videos=videos,
            next_cursor=next_cursor,
            raw_state=state,
            url=url,
        )
