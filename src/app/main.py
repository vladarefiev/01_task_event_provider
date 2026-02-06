import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.infrastructure.database import engine, Base
from app.services.outbox_worker import outbox_worker_loop

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

    # Reset stale "running" lock from previous run (e.g. after crash)
    from app.infrastructure.database import async_session_maker
    from app.infrastructure.repositories.sync_repository import SyncMetadataRepository

    async with async_session_maker() as session:
        sync_repo = SyncMetadataRepository(session)
        meta = await sync_repo.get_or_create()
        if meta.sync_status == "running":
            await sync_repo.update_status("idle")
            await session.commit()
            logger.info("Cleared stale sync status 'running' from previous run")

    # Start outbox worker as a background coroutine
    worker_task = asyncio.create_task(outbox_worker_loop())
    logger.info("Outbox worker started")

    yield

    # Gracefully stop the worker
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        logger.info("Outbox worker stopped")


app = FastAPI(
    title="Events Aggregator",
    lifespan=lifespan,
)
app.include_router(router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"detail": exc.errors()},
    )
