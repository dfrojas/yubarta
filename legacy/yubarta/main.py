from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from yubarta.config import settings
from yubarta.incident.router import router as incident_router
from yubarta.infra.db.initialization import Database
from yubarta.ingestion.router import router as ingestion_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Own the database engine for the process lifetime.

    The engine is built once and disposed on shutdown, and the unit of work built
    from it is what routes reach through their store dependency. Migrations are not
    run here, see `Database`.
    """
    database = Database(settings.DATABASE_URI, echo=settings.DB_ECHO)
    app.state.database = database
    app.state.unit_of_work = database.unit_of_work
    try:
        yield
    finally:
        await database.dispose()


app = FastAPI(title="Yubarta", lifespan=lifespan)
app.include_router(ingestion_router)
app.include_router(incident_router)
