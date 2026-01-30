import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.api.routes import router
from app.config import settings
from app.infrastructure.database import engine, Base

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")

    # Background sync task - runs every 24 hours
    from app.infrastructure.events_provider_client import EventsProviderClient
    from app.services.sync_service import run_sync
    from app.infrastructure.database import async_session_maker

    sync_interval_seconds = 24 * 60 * 60  # 24 hours

    async def sync_loop() -> None:
        await asyncio.sleep(10)  # Wait for app to be ready
        client = EventsProviderClient(
            settings.events_provider_url, settings.events_provider_api_key
        )
        while True:
            try:
                async with async_session_maker() as session:
                    await run_sync(session, client)
            except Exception as e:
                logger.exception("Periodic sync failed: %s", e)
            await asyncio.sleep(sync_interval_seconds)

    sync_task = asyncio.create_task(sync_loop())
    logger.info("Background sync task started")

    yield

    sync_task.cancel()
    try:
        await sync_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Events Aggregator",
    lifespan=lifespan,
)
app.include_router(router)
