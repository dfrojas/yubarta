import asyncio

import pytest

from tests.utils import TestDatabase
from yubarta.config import settings
from yubarta.drivers.db.orm import start_mappers
from yubarta.drivers.db.sessions import get_raw_session
from yubarta.main import app

test_db = TestDatabase()


@pytest.fixture(autouse=True)
def patch_settings(monkeypatch):
    settings.configure(_env_file=".env.ci")


@pytest.fixture(scope="session", autouse=True)
def setup_mappers():
    start_mappers()


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop


@pytest.fixture(scope="session", autouse=True)
async def db():
    """Create and drop test database for each test function"""
    await test_db.setup()
    yield
    await test_db.drop_test_database()


@pytest.fixture(autouse=True)
def override_db():
    app.dependency_overrides[get_raw_session] = test_db.override_get_db()


# @pytest.fixture()
# async def db_session():
#     async with test_db.SessionLocal() as session:
#         yield session
#         await session.rollback()
#         await session.close()

# @pytest.fixture()
# async def client(db_session):
#     def override_get_db():
#         return db_session

#     app.dependency_overrides[get_raw_session] = override_get_db

#     async with AsyncClient(app=app, base_url="http://test") as ac:
#         yield ac

#     app.dependency_overrides.clear()
