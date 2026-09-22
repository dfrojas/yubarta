from collections.abc import AsyncIterator
from uuid import uuid4

import asyncpg
import pytest

from tests.support import Sandbox
from yubarta.drivers.db.initialization import migrate
from yubarta.drivers.db.sessions import Database


@pytest.fixture
async def database_url(sandbox: Sandbox) -> AsyncIterator[str]:
    name = f"test_{uuid4().hex}"
    admin = await asyncpg.connect(sandbox.database_url.replace("postgresql+asyncpg", "postgresql"))
    await admin.execute(f'CREATE DATABASE "{name}"')
    try:
        yield sandbox.database_url.rsplit("/", 1)[0] + "/" + name
    finally:
        await admin.execute(f'DROP DATABASE "{name}" WITH (FORCE)')
        await admin.close()


@pytest.fixture
async def database(database_url: str) -> AsyncIterator[Database]:
    await migrate(database_url)
    database = Database(database_url)
    try:
        yield database
    finally:
        await database.close()
