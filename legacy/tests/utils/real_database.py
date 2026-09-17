"""Real Postgres for integration tests.

The schema is applied by the project's own Alembic migration, not by
`metadata.create_all`. That costs a few seconds per session and buys something the
shortcut cannot: a migration that drifts from the ORM definition fails the suite
instead of passing quietly and only surfacing on a real deploy.
"""

import asyncio
from pathlib import Path

import asyncpg
from alembic import command
from alembic.config import Config

from yubarta.config import settings

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = PROJECT_ROOT / "alembic.ini"
INCIDENT_TABLES = ("incidents", "incident_transitions", "remediation_attempts")


class TestDatabase:
    """Creates, migrates and drops the test database.

    Sync on purpose. Alembic's `env.py` calls `asyncio.run` itself, so driving it
    from inside a running loop would fail; keeping this outside async code avoids
    nesting loops instead of working around it.
    """

    @property
    def _admin_uri(self) -> str:
        return (
            f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}"
            f"@{settings.DB_HOST}:{settings.DB_PORT}/postgres"
        )

    def create(self) -> None:
        asyncio.run(self._recreate_database())
        command.upgrade(self._alembic_config(), "head")

    def drop(self) -> None:
        asyncio.run(self._drop_database())

    def _alembic_config(self) -> Config:
        config = Config(str(ALEMBIC_INI))
        # env.py reads settings.DATABASE_URI, which points at the test database
        # because the settings were configured from .env.ci.
        return config

    async def _recreate_database(self) -> None:
        connection = await asyncpg.connect(self._admin_uri)
        try:
            await connection.execute(f"DROP DATABASE IF EXISTS {settings.DB_NAME} WITH (FORCE)")
            await connection.execute(f"CREATE DATABASE {settings.DB_NAME}")
        finally:
            await connection.close()

    async def _drop_database(self) -> None:
        connection = await asyncpg.connect(self._admin_uri)
        try:
            await connection.execute(f"DROP DATABASE IF EXISTS {settings.DB_NAME} WITH (FORCE)")
        finally:
            await connection.close()
