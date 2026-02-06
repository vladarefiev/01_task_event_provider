from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models import OutboxEvent


class OutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        event_type: str,
        payload: dict[str, Any],
    ) -> OutboxEvent:
        """Create a new outbox record (pending)."""
        record = OutboxEvent(
            event_type=event_type,
            payload=payload,
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def get_pending(self, limit: int = 50, max_attempts: int = 10) -> list[OutboxEvent]:
        """Fetch pending outbox records that haven't exceeded max attempts."""
        stmt = (
            select(OutboxEvent)
            .where(OutboxEvent.is_sent == False, OutboxEvent.attempts < max_attempts)  # noqa: E712
            .order_by(OutboxEvent.created_at)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def mark_sent(self, record_id: uuid.UUID) -> None:
        """Mark outbox record as sent."""
        stmt = (
            update(OutboxEvent)
            .where(OutboxEvent.id == record_id)
            .values(is_sent=True)
        )
        await self._session.execute(stmt)

    async def increment_attempts(self, record_id: uuid.UUID) -> None:
        """Increment attempt counter for failed delivery."""
        stmt = (
            update(OutboxEvent)
            .where(OutboxEvent.id == record_id)
            .values(attempts=OutboxEvent.attempts + 1)
        )
        await self._session.execute(stmt)
