from __future__ import annotations

import logging
from typing import Optional
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class EventsProviderClientError(Exception):
    """Base exception for Events Provider API errors."""

    pass


class EventsProviderClient:
    """HTTP client for Events Provider API."""

    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self._api_key,
            "accept": "application/json",
            "content-type": "application/json",
        }

    def events(self, changed_at: str, cursor: Optional[str] = None) -> dict[str, Any]:
        """
        Fetch events from Events Provider API.
        Uses cursor-based pagination.
        """
        url = f"{self._base_url}/api/events/"
        params: dict[str, str] = {"changed_at": changed_at}
        if cursor:
            params["cursor"] = cursor

        with httpx.Client(timeout=30.0) as client:
            resp = client.get(url, params=params, headers=self._headers())
            resp.raise_for_status()
            return resp.json()

    def events_by_url(self, url: str) -> dict[str, Any]:
        """Fetch events by full URL (for pagination next link)."""
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(url, headers=self._headers())
            resp.raise_for_status()
            return resp.json()

    def seats(self, event_id: str) -> list[str]:
        """Fetch available seats for an event."""
        url = f"{self._base_url}/api/events/{event_id}/seats/"
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(url, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
            return data.get("seats", [])

    def register(
        self,
        event_id: str,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> str:
        """Register for an event. Returns ticket_id."""
        url = f"{self._base_url}/api/events/{event_id}/register/"
        body = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "seat": seat,
        }
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, json=body, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
            return str(data["ticket_id"])

    def unregister(self, event_id: str, ticket_id: str) -> None:
        """Cancel registration for an event."""
        url = f"{self._base_url}/api/events/{event_id}/unregister/"
        with httpx.Client(timeout=30.0) as client:
            resp = client.delete(url, json={"ticket_id": ticket_id}, headers=self._headers())
            resp.raise_for_status()


class EventsPaginator:
    """Iterator over all events from Events Provider API."""

    def __init__(self, client: EventsProviderClient, changed_at: str) -> None:
        self._client = client
        self._changed_at = changed_at

    def __iter__(self) -> "EventsPaginator":
        return self

    def __next__(self) -> dict[str, Any]:
        if not hasattr(self, "_next_url") or self._next_url is None:
            data = self._client.events(self._changed_at)
            self._results = data.get("results", [])
            self._next_url = data.get("next")
            self._idx = 0

        while self._idx < len(self._results):
            event = self._results[self._idx]
            self._idx += 1
            return event

        if self._next_url:
            data = self._client.events_by_url(self._next_url)
            self._results = data.get("results", [])
            self._next_url = data.get("next")
            self._idx = 0
            if self._results:
                event = self._results[0]
                self._idx = 1
                return event

        raise StopIteration
