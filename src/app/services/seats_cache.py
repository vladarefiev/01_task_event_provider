from __future__ import annotations

import time
from typing import Optional


class SeatsCache:
    """In-memory cache for seats with 30 second TTL."""

    TTL_SECONDS = 30

    def __init__(self) -> None:
        self._cache: dict[str, tuple[list[str], float]] = {}

    def get(self, event_id: str) -> Optional[list[str]]:
        entry = self._cache.get(event_id)
        if not entry:
            return None
        seats, timestamp = entry
        if time.time() - timestamp > self.TTL_SECONDS:
            del self._cache[event_id]
            return None
        return seats

    def set(self, event_id: str, seats: list[str]) -> None:
        self._cache[event_id] = (seats, time.time())

    def invalidate(self, event_id: str) -> None:
        """Remove from cache to force fresh fetch on next request."""
        self._cache.pop(event_id, None)
