from __future__ import annotations

import csv
import io
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.models import (
    Platform,
    WatchItemType,
    WatchTier,
)

REQUIRED_CSV_COLUMNS = ("type", "platform", "name", "url_or_id", "tier", "tags", "note", "enabled")
VALID_TYPES = {t.value for t in WatchItemType}
VALID_PLATFORMS = {p.value for p in Platform}
VALID_TIERS = {t.value for t in WatchTier}
MAX_WATCH_ITEMS = 100


@dataclass
class WatchItemCreate:
    type: WatchItemType
    platform: Platform
    name: str
    external_id: str
    url: str | None = None
    tier: WatchTier = WatchTier.GENERAL
    tags: list[str] = field(default_factory=list)
    note: str | None = None
    enabled: bool = True
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class WatchItemUpdate:
    name: str | None = None
    url: str | None = None
    tier: WatchTier | None = None
    tags: list[str] | None = None
    note: str | None = None
    enabled: bool | None = None
    config: dict[str, Any] | None = None


@dataclass
class CsvImportRow:
    row_number: int
    data: WatchItemCreate | None = None
    errors: list[str] = field(default_factory=list)


@dataclass
class CsvImportResult:
    imported: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)
    rows: list[CsvImportRow] = field(default_factory=list)


def parse_tags(raw: str) -> list[str]:
    if not raw or not raw.strip():
        return []
    return [tag.strip() for tag in raw.split(",") if tag.strip()]


def parse_enabled(raw: str) -> bool:
    return raw.strip().lower() in {"true", "1", "yes", "y"}


def validate_csv_headers(fieldnames: list[str] | None) -> list[str]:
    if not fieldnames:
        return ["CSV file is empty or missing header row"]
    missing = [col for col in REQUIRED_CSV_COLUMNS if col not in fieldnames]
    if missing:
        return [f"missing required columns: {', '.join(missing)}"]
    return []


def parse_csv_row(row: dict[str, str], row_number: int) -> CsvImportRow:
    errors: list[str] = []
    item_type = row.get("type", "").strip().lower()
    platform = row.get("platform", "").strip().lower()
    name = row.get("name", "").strip()
    url_or_id = row.get("url_or_id", "").strip()
    tier = row.get("tier", "general").strip().lower()
    tags_raw = row.get("tags", "")
    note = row.get("note", "").strip() or None
    enabled_raw = row.get("enabled", "true")

    if item_type not in VALID_TYPES:
        errors.append(f"invalid type '{item_type}'")
    if platform not in VALID_PLATFORMS:
        errors.append(f"invalid platform '{platform}'")
    if tier not in VALID_TIERS:
        errors.append(f"invalid tier '{tier}'")
    if not name:
        errors.append("name is required")
    if item_type in {"channel", "account"} and not url_or_id:
        errors.append("url_or_id is required for channel/account")
    if item_type in {"keyword", "anime"} and not url_or_id and not name:
        errors.append("url_or_id or name required for keyword/anime")

    if errors:
        return CsvImportRow(row_number=row_number, errors=errors)

    external_id = url_or_id or name
    if item_type in {"keyword", "anime"}:
        external_id = " ".join(external_id.lower().split())

    return CsvImportRow(
        row_number=row_number,
        data=WatchItemCreate(
            type=WatchItemType(item_type),
            platform=Platform(platform),
            name=name,
            external_id=external_id,
            url=url_or_id if item_type in {"channel", "account"} else None,
            tier=WatchTier(tier),
            tags=parse_tags(tags_raw),
            note=note,
            enabled=parse_enabled(enabled_raw),
        ),
    )


def parse_csv_content(content: str, *, existing_count: int = 0) -> CsvImportResult:
    result = CsvImportResult()
    reader = csv.DictReader(io.StringIO(content))
    header_errors = validate_csv_headers(reader.fieldnames)
    if header_errors:
        result.errors.extend(header_errors)
        return result

    for row_number, row in enumerate(reader, start=2):
        if existing_count + result.imported >= MAX_WATCH_ITEMS:
            result.errors.append(f"watchlist limit of {MAX_WATCH_ITEMS} items reached")
            break
        parsed = parse_csv_row(row, row_number)
        result.rows.append(parsed)
        if parsed.errors:
            result.errors.append(f"row {row_number}: {'; '.join(parsed.errors)}")
        elif parsed.data is not None:
            result.imported += 1

    return result


def watch_item_to_dict(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "type": item.type.value,
        "platform": item.platform.value,
        "name": item.name,
        "external_id": item.external_id,
        "url": item.url,
        "tier": item.tier.value,
        "tags": item.tags or [],
        "note": item.note,
        "enabled": item.enabled,
        "config": item.config or {},
        "last_success_at": item.last_success_at,
        "last_attempt_at": item.last_attempt_at,
        "last_status": item.last_status.value if item.last_status else None,
        "consecutive_failures": item.consecutive_failures,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def watch_item_for_adapter(item: Any, known_external_ids: list[str] | None = None) -> dict[str, Any]:
    data = watch_item_to_dict(item)
    data["known_external_ids"] = known_external_ids or []
    return data
