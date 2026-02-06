from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


class CapashinoClientError(Exception):
    pass


class CapashinoClient:
    """HTTP client for Capashino Notification Service API."""

    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    def _headers(self) -> dict[str, str]:
        return {
            "X-API-Key": self._api_key,
            "Content-Type": "application/json",
        }

    def send_notification(
        self,
        message: str,
        reference_id: str,
        idempotency_key: str,
    ) -> dict:
        """Send notification via POST /api/notifications.

        Returns the response body on success.
        Raises CapashinoClientError on non-retryable errors (4xx except 409).
        Raises httpx.HTTPStatusError on server errors (5xx) for retry.
        """
        url = f"{self._base_url}/api/notifications"
        body = {
            "message": message,
            "reference_id": reference_id,
            "idempotency_key": idempotency_key,
        }
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, json=body, headers=self._headers())
            if resp.status_code == 201:
                return resp.json()
            if resp.status_code == 409:
                logger.info("Notification already exists (idempotency_key=%s)", idempotency_key)
                return resp.json()
            if 400 <= resp.status_code < 500:
                raise CapashinoClientError(
                    f"Capashino client error {resp.status_code}: {resp.text}"
                )
            resp.raise_for_status()
            return resp.json()
