from __future__ import annotations

import asyncio
import logging

from app.config import settings
from app.infrastructure.capashino_client import CapashinoClient, CapashinoClientError
from app.infrastructure.database import async_session_maker
from app.infrastructure.repositories.outbox_repository import OutboxRepository

logger = logging.getLogger(__name__)


async def process_outbox() -> None:
    """Process pending outbox records: send notifications to Capashino."""
    capashino = CapashinoClient(settings.capashino_url, settings.capashino_api_key)

    async with async_session_maker() as session:
        repo = OutboxRepository(session)
        pending = await repo.get_pending(
            limit=50, max_attempts=settings.outbox_max_attempts
        )

        for record in pending:
            try:
                payload = record.payload
                capashino.send_notification(
                    message=payload["message"],
                    reference_id=payload["reference_id"],
                    idempotency_key=payload["idempotency_key"],
                )
                await repo.mark_sent(record.id)
                await session.commit()
                logger.info("Outbox record %s sent successfully", record.id)
            except CapashinoClientError:
                logger.exception(
                    "Non-retryable error for outbox record %s", record.id
                )
                await repo.increment_attempts(record.id)
                await session.commit()
            except Exception:
                logger.exception(
                    "Failed to process outbox record %s, will retry", record.id
                )
                await session.rollback()
                await repo.increment_attempts(record.id)
                await session.commit()


async def outbox_worker_loop() -> None:
    """Background loop that polls outbox and processes pending records."""
    logger.info(
        "Outbox worker started (poll_interval=%ds, max_attempts=%d)",
        settings.outbox_poll_interval,
        settings.outbox_max_attempts,
    )
    while True:
        try:
            await process_outbox()
        except Exception:
            logger.exception("Outbox worker iteration failed")
        await asyncio.sleep(settings.outbox_poll_interval)
