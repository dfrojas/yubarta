from collections.abc import AsyncIterator, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tests.utils.real_database import INCIDENT_TABLES, TestDatabase
from yubarta.config import settings
from yubarta.infra.db.repository import SqlAlchemyIncidentStore
from yubarta.infra.db.unit_of_work import SqlAlchemyUnitOfWork
from yubarta.main import app


@pytest.fixture(scope="session", autouse=True)
def test_settings() -> None:
    settings.configure(_env_file=".env.ci")


@pytest.fixture(scope="session")
def incident_database(test_settings: None) -> Iterator[TestDatabase]:
    """Create and migrate the test database once for the whole session.

    Not autouse: unit tests must not pay for a database they never touch.
    """
    database = TestDatabase()
    database.create()
    yield database
    database.drop()


@pytest.fixture()
async def unit_of_work(incident_database: TestDatabase) -> AsyncIterator[SqlAlchemyUnitOfWork]:
    """A unit of work over a per-test engine, against freshly truncated tables.

    The engine is built per test rather than per session because an asyncpg engine is
    bound to the event loop that created it, and pytest-asyncio gives each test its
    own loop.
    """
    engine = create_async_engine(settings.DATABASE_URI, future=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.execute(text(f"TRUNCATE {', '.join(INCIDENT_TABLES)}"))
    try:
        yield SqlAlchemyUnitOfWork(session_factory)
    finally:
        await engine.dispose()


@pytest.fixture()
def incident_store(unit_of_work: SqlAlchemyUnitOfWork) -> SqlAlchemyIncidentStore:
    return SqlAlchemyIncidentStore(unit_of_work)


@pytest.fixture()
def api_client(unit_of_work: SqlAlchemyUnitOfWork) -> Iterator[TestClient]:
    """The real app, over the test database, with its own lifespan-built engine."""
    with TestClient(app) as client:
        yield client
