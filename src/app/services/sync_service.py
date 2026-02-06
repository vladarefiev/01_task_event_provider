import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.events_provider_client import EventsPaginator, EventsProviderClient
from app.infrastructure.repositories.event_repository import EventRepository
from app.infrastructure.repositories.sync_repository import SyncMetadataRepository

logger = logging.getLogger(__name__)

FIRST_SYNC_DATE = "2000-01-01"
COMMIT_BATCH_SIZE = 500  # commit every N events so data is visible during long syncs


async def run_sync(
    session: AsyncSession,
    client: EventsProviderClient,
    changed_at_override: str | None = None,
) -> None:
    """Run full sync from Events Provider API."""
    sync_repo = SyncMetadataRepository(session)
    event_repo = EventRepository(session)

    meta = await sync_repo.get_or_create()
    if meta.sync_status == "running":
        logger.warning("Sync already running, skipping")
        return

    await sync_repo.update_status("running")
    await session.commit()

    try:
        changed_at = (
            changed_at_override
            if changed_at_override is not None
            else (meta.last_changed_at or FIRST_SYNC_DATE)
        )
        logger.info("Starting sync with changed_at=%s", changed_at)

        max_changed_at = changed_at
        count = 0

        paginator = EventsPaginator(client, changed_at)
        for event_data in paginator:
            place_data = event_data.get("place", {})
            if not place_data:
                continue
            place = await event_repo.upsert_place(place_data)
            await event_repo.upsert_event(event_data, place)
            count += 1
            logger.info("Processed event %d: %s", count, event_data["id"])

            for change_key in ("changed_at", "status_changed_at"):
                event_changed = event_data.get(change_key)
                if event_changed:
                    dt = event_changed[:10]  # YYYY-MM-DD
                    if dt > max_changed_at:
                        max_changed_at = dt

            if count % COMMIT_BATCH_SIZE == 0:
                await session.commit()
                logger.info("Committed batch: %d events so far", count)

        await sync_repo.update_status(
            "success",
            last_sync_time=datetime.now(),
            last_changed_at=max_changed_at,
        )
        await session.commit()
        logger.info("Sync completed: %d events processed", count)
    except Exception as e:
        logger.exception("Sync failed: %s", e)
        await sync_repo.update_status("error")
        await session.commit()
        raise
