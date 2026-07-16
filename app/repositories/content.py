from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ContentItem, Platform


class ContentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_known_external_ids(
        self,
        platform: Platform,
        external_ids: list[str],
    ) -> set[str]:
        if not external_ids:
            return set()
        stmt = select(ContentItem.external_id).where(
            ContentItem.platform == platform,
            ContentItem.external_id.in_(external_ids),
        )
        result = await self._session.scalars(stmt)
        return set(result.all())

    async def get_all_external_ids_for_platform(self, platform: Platform) -> set[str]:
        stmt = select(ContentItem.external_id).where(ContentItem.platform == platform)
        result = await self._session.scalars(stmt)
        return set(result.all())

    async def upsert_content(
        self,
        *,
        platform: Platform,
        normalized: dict[str, Any],
        source_watch_item_id: uuid.UUID | None,
    ) -> tuple[ContentItem, bool]:
        now = datetime.now(UTC)
        values = {
            "platform": platform,
            "external_id": normalized["external_id"],
            "source_watch_item_id": source_watch_item_id,
            "channel_external_id": normalized.get("channel_external_id"),
            "channel_name": normalized.get("channel_name"),
            "title_original": normalized.get("title_original", ""),
            "title_zh": normalized.get("title_zh"),
            "description": normalized.get("description"),
            "tags": normalized.get("tags") or [],
            "published_at": normalized.get("published_at"),
            "duration_seconds": normalized.get("duration_seconds"),
            "url": normalized.get("url"),
            "thumbnail_url": normalized.get("thumbnail_url"),
            "language": normalized.get("language"),
            "region": normalized.get("region"),
            "raw_payload": normalized.get("raw_payload"),
            "first_seen_at": now,
            "last_seen_at": now,
        }

        stmt = (
            insert(ContentItem)
            .values(**values)
            .on_conflict_do_update(
                index_elements=["platform", "external_id"],
                set_={
                    "channel_external_id": values["channel_external_id"],
                    "channel_name": values["channel_name"],
                    "title_original": values["title_original"],
                    "description": values["description"],
                    "tags": values["tags"],
                    "published_at": values["published_at"],
                    "duration_seconds": values["duration_seconds"],
                    "url": values["url"],
                    "thumbnail_url": values["thumbnail_url"],
                    "language": values["language"],
                    "raw_payload": values["raw_payload"],
                    "last_seen_at": now,
                },
            )
            .returning(ContentItem.id)
        )
        result = await self._session.execute(stmt)
        row_id = result.scalar_one()

        item = await self._session.get(ContentItem, row_id)
        assert item is not None

        is_new = item.first_seen_at == item.last_seen_at or (
            (now - item.first_seen_at).total_seconds() < 1
        )
        return item, is_new

    async def get_by_ids(self, ids: list[uuid.UUID]) -> dict[uuid.UUID, ContentItem]:
        if not ids:
            return {}
        stmt = select(ContentItem).where(ContentItem.id.in_(ids))
        items = (await self._session.scalars(stmt)).all()
        return {item.id: item for item in items}
