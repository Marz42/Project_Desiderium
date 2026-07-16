"""Versioned TikTok page structure selectors for scrape isolation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SelectorVersion:
    name: str
    state_script_ids: tuple[str, ...]
    cookie_expiry_markers: tuple[str, ...]
    login_url_fragments: tuple[str, ...]


SELECTOR_VERSIONS: dict[str, SelectorVersion] = {
    "v1": SelectorVersion(
        name="v1",
        state_script_ids=("SIGI_STATE", "__UNIVERSAL_DATA_FOR_REHYDRATION__"),
        cookie_expiry_markers=(
            "login-modal",
            '"status_code":10000',
            "captcha-verify",
            "verify-center",
            "session expired",
        ),
        login_url_fragments=("/login", "passport/web"),
    ),
}


def get_selector_version(version: str) -> SelectorVersion:
    if version not in SELECTOR_VERSIONS:
        raise ValueError(f"unknown TikTok selector version: {version}")
    return SELECTOR_VERSIONS[version]


def extract_embedded_json(html: str, *, version: str) -> dict[str, Any]:
    """Extract embedded state JSON from a TikTok HTML page."""
    selectors = get_selector_version(version)

    for script_id in selectors.state_script_ids:
        pattern = re.compile(
            rf'<script[^>]+id="{re.escape(script_id)}"[^>]*>(?P<payload>.*?)</script>',
            re.DOTALL,
        )
        match = pattern.search(html)
        if not match:
            continue
        payload = match.group("payload").strip()
        if not payload:
            continue
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data

    raise ValueError(f"no embedded state found for selector version {version}")


def is_cookie_expired_response(
    *,
    status_code: int,
    url: str,
    body: str,
    version: str,
) -> bool:
    selectors = get_selector_version(version)
    if status_code in {401, 403}:
        return True
    lowered = body.lower()
    if any(marker.lower() in lowered for marker in selectors.cookie_expiry_markers):
        return True
    return any(fragment in url for fragment in selectors.login_url_fragments)


def _walk_collect_videos(node: Any, found: list[dict[str, Any]]) -> None:
    if isinstance(node, dict):
        if "id" in node and ("desc" in node or "createTime" in node):
            video_id = str(node.get("id", ""))
            if video_id.isdigit() and len(video_id) >= 10:
                found.append(node)
        for value in node.values():
            _walk_collect_videos(value, found)
    elif isinstance(node, list):
        for item in node:
            _walk_collect_videos(item, found)


def extract_videos_from_state(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect video-like dicts from parsed page state."""
    found: list[dict[str, Any]] = []
    item_module = state.get("ItemModule")
    if isinstance(item_module, dict):
        for value in item_module.values():
            if isinstance(value, dict):
                found.append(value)

    for key in ("ItemList", "itemList", "items"):
        block = state.get(key)
        if isinstance(block, dict):
            for value in block.values():
                if isinstance(value, dict) and "itemList" in value:
                    items = value.get("itemList")
                    if isinstance(items, list):
                        found.extend(item for item in items if isinstance(item, dict))

    _walk_collect_videos(state, found)

    deduped: dict[str, dict[str, Any]] = {}
    for video in found:
        vid = str(video.get("id", ""))
        if vid:
            deduped[vid] = video
    return list(deduped.values())


def extract_cursor(state: dict[str, Any]) -> str | None:
    for key in ("cursor", "nextCursor", "hasMore"):
        if key in state and state[key] not in (None, "", False, 0):
            if key == "hasMore" and not state[key]:
                return None
            if key == "hasMore":
                cursor = state.get("cursor") or state.get("nextCursor")
                return str(cursor) if cursor else None
            return str(state[key])

    for node in _iter_dicts(state):
        if "cursor" in node and node.get("hasMore") is True:
            return str(node["cursor"])
    return None


def _iter_dicts(node: Any):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _iter_dicts(value)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_dicts(item)
