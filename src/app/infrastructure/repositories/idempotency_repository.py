from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models import IdempotencyRecord


class IdempotencyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_key(self, idempotency_key: str) -> Optional[IdempotencyRecord]:
        """Find existing record by idempotency key."""
        stmt = select(IdempotencyRecord).where(
            IdempotencyRecord.idempotency_key == idempotency_key
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        idempotency_key: str,
        request_hash: str,
        ticket_id: uuid.UUID,
    ) -> IdempotencyRecord:
        """Save successful result keyed by idempotency key."""
        record = IdempotencyRecord(
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            ticket_id=ticket_id,
        )
        self._session.add(record)
        await self._session.flush()
        return record
