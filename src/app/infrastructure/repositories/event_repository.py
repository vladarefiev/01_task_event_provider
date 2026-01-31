from __future__ import annotations

import uuid
from typing import Optional
from datetime import date, datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.infrastructure.models import Event, Place


class EventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_place(self, place_data: dict) -> Place:
        """Insert or update place."""
        place_id = uuid.UUID(place_data["id"])
        stmt = select(Place).where(Place.id == place_id)
        result = await self._session.execute(stmt)
        place = result.scalar_one_or_none()

        if place:
            place.name = place_data["name"]
            place.city = place_data["city"]
            place.address = place_data["address"]
            place.seats_pattern = place_data.get("seats_pattern")
        else:
            place = Place(
                id=place_id,
                name=place_data["name"],
                city=place_data["city"],
                address=place_data["address"],
                seats_pattern=place_data.get("seats_pattern"),
            )
            self._session.add(place)
            await self._session.flush()
        return place

    async def upsert_event(self, event_data: dict, place: Place) -> Event:
        """Insert or update event."""
        event_id = uuid.UUID(event_data["id"])
        stmt = select(Event).where(Event.id == event_id)
        result = await self._session.execute(stmt)
        event = result.scalar_one_or_none()

        event_time = datetime.fromisoformat(event_data["event_time"].replace("Z", "+00:00"))
        reg_deadline = datetime.fromisoformat(
            event_data["registration_deadline"].replace("Z", "+00:00")
        )
        changed_at = None
        if event_data.get("changed_at"):
            changed_at = datetime.fromisoformat(event_data["changed_at"].replace("Z", "+00:00"))

        if event:
            event.name = event_data["name"]
            event.place_id = place.id
            event.event_time = event_time
            event.registration_deadline = reg_deadline
            event.status = event_data["status"]
            event.number_of_visitors = event_data.get("number_of_visitors", 0)
            event.changed_at = changed_at
        else:
            event = Event(
                id=event_id,
                name=event_data["name"],
                place_id=place.id,
                event_time=event_time,
                registration_deadline=reg_deadline,
                status=event_data["status"],
                number_of_visitors=event_data.get("number_of_visitors", 0),
                changed_at=changed_at,
            )
            self._session.add(event)
            await self._session.flush()
        return event

    async def list_events(
        self,
        date_from: Optional[date] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Event], int]:
        """List events with optional date filter and pagination."""
        conditions = []
        if date_from:
            conditions.append(Event.event_time >= datetime.combine(date_from, datetime.min.time()))

        base_query = select(Event).options(joinedload(Event.place)).join(Place)
        count_query = select(func.count()).select_from(Event).join(Place)
        if conditions:
            base_query = base_query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        result = await self._session.execute(count_query)
        total = result.scalar_one()

        offset = (page - 1) * page_size
        base_query = base_query.order_by(Event.event_time).offset(offset).limit(page_size)
        result = await self._session.execute(base_query)
        events = list(result.scalars().all())
        return events, total

    async def get_by_id(self, event_id: uuid.UUID) -> Optional[Event]:
        """Get event by ID."""
        stmt = select(Event).options(joinedload(Event.place)).where(Event.id == event_id)
        result = await self._session.execute(stmt)
        return result.unique().scalar_one_or_none()
