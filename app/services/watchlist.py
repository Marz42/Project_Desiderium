from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.youtube import YouTubeAdapter, YouTubeClient
from app.config import Settings, get_settings
from app.models import Platform, WatchItemType, WatchTier
from app.repositories.watchlist import WatchlistRepository
from app.schemas.watchlist import (
    MAX_WATCH_ITEMS,
    CsvImportResult,
    WatchItemCreate,
    WatchItemUpdate,
    parse_csv_content,
    watch_item_to_dict,
)

logger = logging.getLogger(__name__)


class WatchlistService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._repo = WatchlistRepository(session)

    async def list_items(
        self,
        *,
        tier: WatchTier | None = None,
        enabled_only: bool = False,
    ) -> list[dict]:
        items = await self._repo.list_items(tier=tier, enabled_only=enabled_only)
        return [watch_item_to_dict(item) for item in items]

    async def get_item(self, item_id: uuid.UUID) -> dict | None:
        item = await self._repo.get_by_id(item_id)
        if item is None:
            return None
        return watch_item_to_dict(item)

    async def create_item(self, data: WatchItemCreate) -> dict:
        count = await self._repo.count()
        if count >= MAX_WATCH_ITEMS:
            raise ValueError(f"watchlist limit of {MAX_WATCH_ITEMS} items reached")

        if data.platform == Platform.YOUTUBE and data.type in {
            WatchItemType.CHANNEL,
            WatchItemType.ACCOUNT,
        }:
            data = await self._resolve_youtube_channel(data)

        existing = await self._repo.find_by_unique_key(
            data.platform.value,
            data.type.value,
            data.external_id,
        )
        if existing:
            raise ValueError("duplicate watch item: platform+type+external_id already exists")

        item = await self._repo.create(data)
        await self._session.commit()
        return watch_item_to_dict(item)

    async def update_item(self, item_id: uuid.UUID, data: WatchItemUpdate) -> dict:
        item = await self._repo.get_by_id(item_id)
        if item is None:
            raise ValueError("watch item not found")
        updated = await self._repo.update(item, data)
        await self._session.commit()
        return watch_item_to_dict(updated)

    async def toggle_enabled(self, item_id: uuid.UUID) -> dict:
        item = await self._repo.get_by_id(item_id)
        if item is None:
            raise ValueError("watch item not found")
        updated = await self._repo.update(item, WatchItemUpdate(enabled=not item.enabled))
        await self._session.commit()
        return watch_item_to_dict(updated)

    async def delete_item(self, item_id: uuid.UUID) -> None:
        item = await self._repo.get_by_id(item_id)
        if item is None:
            raise ValueError("watch item not found")
        await self._repo.delete(item)
        await self._session.commit()

    async def import_csv(self, content: str) -> CsvImportResult:
        existing_count = await self._repo.count()
        parsed = parse_csv_content(content, existing_count=existing_count)
        if parsed.errors and not any(row.data for row in parsed.rows):
            return parsed

        imported = 0
        skipped = 0
        for row in parsed.rows:
            if row.data is None:
                skipped += 1
                continue
            try:
                data = row.data
                if data.platform == Platform.YOUTUBE and data.type in {
                    WatchItemType.CHANNEL,
                    WatchItemType.ACCOUNT,
                }:
                    data = await self._resolve_youtube_channel(data)

                existing = await self._repo.find_by_unique_key(
                    data.platform.value,
                    data.type.value,
                    data.external_id,
                )
                if existing:
                    skipped += 1
                    parsed.errors.append(
                        f"row {row.row_number}: duplicate skipped ({data.external_id})"
                    )
                    continue

                if await self._repo.count() >= MAX_WATCH_ITEMS:
                    parsed.errors.append(f"watchlist limit of {MAX_WATCH_ITEMS} reached")
                    break

                await self._repo.create(data)
                imported += 1
            except Exception as exc:  # noqa: BLE001
                skipped += 1
                parsed.errors.append(f"row {row.row_number}: {exc}")

        parsed.imported = imported
        parsed.skipped = skipped
        await self._session.commit()
        return parsed

    async def _resolve_youtube_channel(self, data: WatchItemCreate) -> WatchItemCreate:
        if data.external_id.startswith("UC") and len(data.external_id) == 24:
            return data
        client = YouTubeClient(
            self._settings.youtube_api_key,
            max_search_calls=self._settings.youtube_max_search_calls,
            daily_quota_limit=self._settings.youtube_daily_quota_limit,
        )
        adapter = YouTubeAdapter(client)
        try:
            resolved = await adapter.resolve_external_id(
                data.type.value,
                data.url or data.external_id,
                data.name,
            )
        finally:
            await adapter.close()
        return WatchItemCreate(
            type=data.type,
            platform=data.platform,
            name=data.name,
            external_id=resolved,
            url=data.url or data.external_id,
            tier=data.tier,
            tags=data.tags,
            note=data.note,
            enabled=data.enabled,
            config=data.config,
        )
