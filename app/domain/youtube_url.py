"""Parse YouTube video IDs from published URLs (watch/short/share link forms)."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")

_ALLOWED_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
    "youtu.be",
}


def _valid_id(candidate: str | None) -> str | None:
    if candidate and _VIDEO_ID_RE.fullmatch(candidate):
        return candidate
    return None


def parse_youtube_video_id(url: str | None) -> str | None:
    """Extract an 11-character YouTube video ID from a public URL.

    Supports ``watch?v=``, ``youtu.be/``, ``shorts/``, and ``embed/`` forms.
    Returns ``None`` if the URL is missing, malformed, or not a recognized
    YouTube host.
    """
    if not url:
        return None
    value = url.strip()
    if not value:
        return None
    if "//" not in value:
        value = f"https://{value}"

    try:
        parsed = urlparse(value)
    except ValueError:
        return None

    host = (parsed.hostname or "").lower()
    if host not in _ALLOWED_HOSTS:
        return None

    path = parsed.path or ""
    segments = [seg for seg in path.split("/") if seg]

    if host == "youtu.be":
        if not segments:
            return None
        return _valid_id(segments[0])

    if segments and segments[0] in {"shorts", "embed", "live", "v"} and len(segments) >= 2:
        return _valid_id(segments[1])

    if path in ("/watch", "") or segments and segments[0] == "watch":
        query = parse_qs(parsed.query)
        values = query.get("v")
        if values:
            return _valid_id(values[0])
        return None

    return None
