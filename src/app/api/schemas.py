from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


class PlaceResponse(BaseModel):
    id: UUID
    name: str
    city: str
    address: str

    class Config:
        from_attributes = True


class PlaceDetailResponse(PlaceResponse):
    seats_pattern: Optional[str] = None


class EventListResponse(BaseModel):
    id: UUID
    name: str
    place: PlaceResponse
    event_time: datetime
    registration_deadline: datetime
    status: str
    number_of_visitors: int

    class Config:
        from_attributes = True


class EventDetailResponse(BaseModel):
    id: UUID
    name: str
    place: PlaceDetailResponse
    event_time: datetime
    registration_deadline: datetime
    status: str
    number_of_visitors: int

    class Config:
        from_attributes = True


class EventsListResponse(BaseModel):
    count: int
    next: Optional[str] = None
    previous: Optional[str] = None
    results: list[EventListResponse]


class SeatsResponse(BaseModel):
    event_id: UUID
    available_seats: list[str]


class TicketCreateRequest(BaseModel):
    event_id: UUID
    first_name: str
    last_name: str
    email: EmailStr
    seat: str


class TicketCreateResponse(BaseModel):
    ticket_id: UUID


class TicketDeleteResponse(BaseModel):
    success: bool = True
