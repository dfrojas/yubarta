from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from yubarta.config import settings
from yubarta.drivers.db.initialization import Database


async def get_fastapi_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions, use with Depends
    class to inject the session into the request.
    """
    from yubarta.main import app

    db = app.state.db
    session = await db.get_session()

    try:
        yield session
    finally:
        await session.close()


# We take it out of the function to avoid instance the Database class in each call of the function.
_db = Database(settings.DATABASE_URI)


@asynccontextmanager
async def get_raw_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a raw database session to inject in non-FastAPI code."""
    session = await _db.get_session()
    try:
        yield session
    finally:
        await session.close()
