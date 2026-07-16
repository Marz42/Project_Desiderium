"""Load watchlist CSV and normalize entries."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

DEFAULT_WATCHLIST = Path(__file__).parent / "watchlist.csv"


@dataclass(frozen=True)
class WatchItem:
    type: str
    platform: str
    name: str
    url_or_id: str
    tier: str
    tags: str
    note: str
    enabled: bool


def load_watchlist(path: Path | None = None) -> list[WatchItem]:
    path = path or DEFAULT_WATCHLIST
    items: list[WatchItem] = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("enabled", "true").lower() != "true":
                continue
            items.append(
                WatchItem(
                    type=row["type"].strip(),
                    platform=row["platform"].strip(),
                    name=row["name"].strip(),
                    url_or_id=row.get("url_or_id", "").strip(),
                    tier=row.get("tier", "general").strip(),
                    tags=row.get("tags", "").strip(),
                    note=row.get("note", "").strip(),
                    enabled=True,
                )
            )
    return items


def channels(items: list[WatchItem]) -> list[WatchItem]:
    return [item for item in items if item.type == "channel"]


def keywords(items: list[WatchItem]) -> list[WatchItem]:
    return [item for item in items if item.type == "keyword"]


def anime_titles(items: list[WatchItem]) -> list[WatchItem]:
    return [item for item in items if item.type == "anime"]
