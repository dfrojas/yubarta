import asyncio

import pytest

from tests.utils.real_database import TestDatabase
from yubarta.config import settings
from yubarta.infra.db.orm import start_mappers
from yubarta.infra.db.sessions import get_raw_session
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


@pytest.fixture(scope="session")
async def db():
    """Real database — opt-in for integration tests only."""
    await test_db.setup()
    yield
    await test_db.drop_test_database()


@pytest.fixture()
def override_db(db):
    app.dependency_overrides[get_raw_session] = test_db.override_get_db()
