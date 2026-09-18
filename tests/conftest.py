"""Test Postgres harness: one ephemeral cluster per session, one fresh DB per test.

Every test gets a real PostgreSQL database cloned from an Alembic-migrated
template. The per-test database is dropped after the test finishes.
"""

from __future__ import annotations

import getpass
import os
import re
import shutil
import socket
import subprocess
import uuid
from pathlib import Path

import asyncpg
import pytest

from yubarta.persistence.session import create_engine, create_session_factory

ROOT = Path(__file__).resolve().parents[1]
_DB_NAME_PATTERN = re.compile(r"^[a-z0-9_]+$")


def _quote(name: str) -> str:
    if not _DB_NAME_PATTERN.match(name):
        raise ValueError(f"Unsafe database name: {name}")
    return f'"{name}"'


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


async def _wait_ready(dsn: str, timeout: float = 30.0) -> None:
    import asyncio

    deadline = asyncio.get_event_loop().time() + timeout
    last_error: Exception | None = None
    while asyncio.get_event_loop().time() < deadline:
        try:
            conn = await asyncpg.connect(dsn)
            await conn.close()
            return
        except Exception as exc:
            last_error = exc
            await asyncio.sleep(0.2)
    raise ConnectionError(f"Postgres not ready: {dsn}: {last_error}")


@pytest.fixture(scope="session")
async def pg_cluster(tmp_path_factory):  # type: ignore[no-untyped-def]
    """Provide (admin_dsn, user, host, port). Starts an ephemeral cluster unless overridden."""
    override = os.environ.get("YUBARTA_TEST_POSTGRES_URL", "")
    if override:
        yield override
        return
    for binary in ("initdb", "pg_ctl"):
        if shutil.which(binary) is None:
            raise RuntimeError(f"Missing {binary}; install Postgres or set YUBARTA_TEST_POSTGRES_URL")
    data_dir = tmp_path_factory.mktemp("pgdata")
    user = getpass.getuser()
    port = _free_port()
    subprocess.run(["initdb", "-D", str(data_dir), "-E", "UTF8"], check=True, capture_output=True)
    subprocess.run(
        ["pg_ctl", "-D", str(data_dir), "-o", f"-p {port} -c listen_addresses='127.0.0.1'", "-l", str(data_dir / "log"), "-w", "start"],
        check=True,
        capture_output=True,
    )
    admin_dsn = f"postgresql://{user}@127.0.0.1:{port}/postgres"
    try:
        await _wait_ready(admin_dsn)
        yield admin_dsn
    finally:
        subprocess.run(["pg_ctl", "-D", str(data_dir), "-m", "fast", "stop"], capture_output=True)


def _sync_dsn(admin_dsn: str, dbname: str) -> str:
    base = admin_dsn.replace("postgresql://", "postgresql+psycopg://", 1).rsplit("/", 1)[0]
    return f"{base}/{dbname}"


@pytest.fixture(scope="session")
async def pg_template(pg_cluster):  # type: ignore[no-untyped-def]
    """Create one Alembic-migrated template database for the whole test session."""
    template = f"yubarta_tpl_{os.getpid()}_{uuid.uuid4().hex[:8]}"
    conn = await asyncpg.connect(pg_cluster)
    try:
        await conn.execute(f"CREATE DATABASE {_quote(template)}")
    finally:
        await conn.close()
    previous = os.environ.get("YUBARTA_DATABASE_URL")
    os.environ["YUBARTA_DATABASE_URL"] = _sync_dsn(pg_cluster, template)
    try:
        # Subprocess: guarantees all migration connections close before cloning.
        subprocess.run(
            ["python3", "-m", "alembic", "upgrade", "head"],
            check=True,
            capture_output=True,
            cwd=str(ROOT),
        )
    finally:
        if previous is None:
            os.environ.pop("YUBARTA_DATABASE_URL", None)
        else:
            os.environ["YUBARTA_DATABASE_URL"] = previous
    yield pg_cluster, template
    conn = await asyncpg.connect(pg_cluster)
    try:
        await conn.execute(f"DROP DATABASE {_quote(template)} WITH (FORCE)")
    finally:
        await conn.close()


@pytest.fixture()
async def test_db(pg_template):  # type: ignore[no-untyped-def]
    """Fresh real Postgres database per test, dropped afterwards. Returns async SQLAlchemy URL."""
    admin_dsn, template = pg_template
    dbname = f"yubarta_t_{uuid.uuid4().hex[:12]}"
    conn = await asyncpg.connect(admin_dsn)
    try:
        await conn.execute(f"CREATE DATABASE {_quote(dbname)} TEMPLATE {_quote(template)}")
    finally:
        await conn.close()
    async_url = admin_dsn.replace("postgresql://", "postgresql+asyncpg://", 1).rsplit("/", 1)[0] + f"/{dbname}"
    yield async_url
    conn = await asyncpg.connect(admin_dsn)
    try:
        await conn.execute(f"DROP DATABASE {_quote(dbname)} WITH (FORCE)")
    finally:
        await conn.close()


@pytest.fixture()
async def session_factory(test_db):  # type: ignore[no-untyped-def]
    engine = create_engine(test_db)
    factory = create_session_factory(engine)
    yield factory
    await engine.dispose()
