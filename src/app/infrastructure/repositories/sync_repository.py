from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models import SyncMetadata


class SyncMetadataRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self) -> SyncMetadata:
        """Get single sync metadata row, create if not exists."""
        stmt = select(SyncMetadata).limit(1)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if not row:
            row = SyncMetadata()
            self._session.add(row)
            await self._session.flush()
        return row

    async def update_status(
        self,
        status: str,
        last_sync_time: Optional[datetime] = None,
        last_changed_at: Optional[str] = None,
    ) -> None:
        """Update sync status."""
        row = await self.get_or_create()
        row.sync_status = status
        if last_sync_time is not None:
            row.last_sync_time = last_sync_time
        if last_changed_at is not None:
            row.last_changed_at = last_changed_at
