from __future__ import annotations

import logging
from typing import Optional
import uuid
from datetime import date, datetime, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    EventDetailResponse,
    EventListResponse,
    EventsListResponse,
    PlaceDetailResponse,
    PlaceResponse,
    SeatsResponse,
    TicketCreateRequest,
    TicketCreateResponse,
    TicketDeleteResponse,
)
from app.config import settings
from app.infrastructure.database import async_session_maker, get_db
from app.infrastructure.events_provider_client import EventsProviderClient
from app.infrastructure.models import Event, Place
from app.infrastructure.repositories.event_repository import EventRepository
from app.infrastructure.repositories.ticket_repository import TicketRepository
from app.services.sync_service import run_sync

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["api"])

# Shared state
_sync_lock: bool = False


async def _run_sync_background(changed_at: Optional[datetime] = None) -> None:
    global _sync_lock
    if _sync_lock:
        logger.warning("Sync already in progress, skipping")
        return
    _sync_lock = True
    try:
        client = EventsProviderClient(
            settings.events_provider_url, settings.events_provider_api_key
        )
        changed_at_str = changed_at.strftime("%Y-%m-%d") if changed_at else None
        async with async_session_maker() as session:
            await run_sync(session, client, changed_at_override=changed_at_str)
    finally:
        _sync_lock = False


def _place_to_response(place: Place, include_seats_pattern: bool = False):
    data = {"id": place.id, "name": place.name, "city": place.city, "address": place.address}
    if include_seats_pattern:
        return PlaceDetailResponse(**data, seats_pattern=place.seats_pattern)
    return PlaceResponse(**data)


def _event_to_list_response(event: Event) -> EventListResponse:
    return EventListResponse(
        id=event.id,
        name=event.name,
        place=_place_to_response(event.place),
        event_time=event.event_time,
        registration_deadline=event.registration_deadline,
        status=event.status,
        number_of_visitors=event.number_of_visitors,
    )


def _event_to_detail_response(event: Event) -> EventDetailResponse:
    return EventDetailResponse(
        id=event.id,
        name=event.name,
        place=_place_to_response(event.place, include_seats_pattern=True),
        event_time=event.event_time,
        registration_deadline=event.registration_deadline,
        status=event.status,
        number_of_visitors=event.number_of_visitors,
    )


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/sync/trigger")
async def trigger_sync(
    background_tasks: BackgroundTasks,
    changed_at: Optional[datetime] = Query(None, description="Sync events changed from this date (ISO format)"),
) -> dict[str, str]:
    background_tasks.add_task(_run_sync_background, changed_at)
    return {"status": "started"}


@router.get("/events", response_model=EventsListResponse)
async def list_events(
    request: Request,
    session: AsyncSession = Depends(get_db),
    date_from: Optional[date] = None,
    page: int = 1,
    page_size: int = 20,
) -> EventsListResponse:
    event_repo = EventRepository(session)
    events, total = await event_repo.list_events(
        date_from=date_from, page=page, page_size=page_size
    )

    base_url = str(request.base_url).rstrip("/")
    next_url = None
    prev_url = None
    base_params: dict = {"page_size": page_size}
    if date_from:
        base_params["date_from"] = str(date_from)
    if page * page_size < total:
        next_params = {**base_params, "page": page + 1}
        next_url = f"{base_url}/api/events?{urlencode(next_params)}"
    if page > 1:
        prev_params = {**base_params, "page": page - 1}
        prev_url = f"{base_url}/api/events?{urlencode(prev_params)}"

    return EventsListResponse(
        count=total,
        next=next_url,
        previous=prev_url,
        results=[_event_to_list_response(e) for e in events],
    )


@router.get("/events/{event_id}", response_model=EventDetailResponse)
async def get_event(
    event_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> EventDetailResponse:
    event_repo = EventRepository(session)
    event = await event_repo.get_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return _event_to_detail_response(event)


@router.get("/events/{event_id}/seats", response_model=SeatsResponse)
async def get_seats(
    event_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> SeatsResponse:
    event_repo = EventRepository(session)
    event = await event_repo.get_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.status != "published":
        raise HTTPException(status_code=400, detail="Event is not published for registration")

    client = EventsProviderClient(settings.events_provider_url, settings.events_provider_api_key)
    seats = client.seats(str(event_id))
    return SeatsResponse(event_id=event_id, available_seats=seats)


@router.post("/tickets", response_model=TicketCreateResponse, status_code=201)
async def create_ticket(
    body: TicketCreateRequest,
    session: AsyncSession = Depends(get_db),
) -> TicketCreateResponse:
    event_repo = EventRepository(session)
    event = await event_repo.get_by_id(body.event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.status != "published":
        raise HTTPException(status_code=400, detail="Event is not published for registration")
    now = datetime.now(timezone.utc)
    reg_deadline = event.registration_deadline
    if reg_deadline.tzinfo is None:
        reg_deadline = reg_deadline.replace(tzinfo=timezone.utc)
    if reg_deadline < now:
        raise HTTPException(status_code=400, detail="Registration deadline has passed")

    # Check seat availability
    client = EventsProviderClient(
        settings.events_provider_url, settings.events_provider_api_key
    )
    available_seats = client.seats(str(body.event_id))
    if body.seat not in available_seats:
        raise HTTPException(status_code=400, detail="Seat is not available")

    provider_ticket_id = client.register(
        event_id=str(body.event_id),
        first_name=body.first_name,
        last_name=body.last_name,
        email=str(body.email),
        seat=body.seat,
    )

    ticket_repo = TicketRepository(session)
    ticket = await ticket_repo.create(
        event_id=body.event_id,
        provider_ticket_id=uuid.UUID(provider_ticket_id),
        first_name=body.first_name,
        last_name=body.last_name,
        email=str(body.email),
        seat=body.seat,
    )

    return TicketCreateResponse(ticket_id=ticket.provider_ticket_id)


@router.delete("/tickets/{ticket_id}", response_model=TicketDeleteResponse)
async def delete_ticket(
    ticket_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> TicketDeleteResponse:
    ticket_repo = TicketRepository(session)
    ticket = await ticket_repo.get_by_provider_ticket_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    client = EventsProviderClient(settings.events_provider_url, settings.events_provider_api_key)
    client.unregister(event_id=str(ticket.event_id), ticket_id=str(ticket_id))
    await session.delete(ticket)
    return TicketDeleteResponse()
