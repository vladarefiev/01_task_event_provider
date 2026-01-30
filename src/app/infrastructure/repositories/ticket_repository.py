from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models import Ticket


class TicketRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        event_id: uuid.UUID,
        provider_ticket_id: uuid.UUID,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> Ticket:
        """Create ticket record."""
        ticket = Ticket(
            event_id=event_id,
            provider_ticket_id=provider_ticket_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            seat=seat,
        )
        self._session.add(ticket)
        await self._session.flush()
        return ticket

    async def get_by_provider_ticket_id(self, provider_ticket_id: uuid.UUID) -> Optional[Ticket]:
        """Get ticket by provider's ticket_id (used for DELETE)."""
        stmt = select(Ticket).where(Ticket.provider_ticket_id == provider_ticket_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
