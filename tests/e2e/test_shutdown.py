import asyncio
import signal
from time import monotonic

import asyncpg
import pytest

from tests.support import Daemon, Sandbox

pytestmark = pytest.mark.e2e


async def test_sigterm_closes_scanner_and_database(daemon: Daemon, sandbox: Sandbox, database_url: str) -> None:
    await daemon.wait_scanner()
    before = await asyncio.to_thread(sandbox.command, "pgrep", "-c", "tail")
    assert int(before.strip()) >= 1
    started = monotonic()
    await daemon.stop()
    assert monotonic() - started < 10
    # Uvicorn re-raises the original signal after lifespan cleanup.
    assert daemon.process.returncode == -signal.SIGTERM
    assert "Application shutdown complete." in daemon.log.read_text()
    connection = await asyncpg.connect(database_url.replace("postgresql+asyncpg", "postgresql"))
    try:
        count = await connection.fetchval("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND pid <> pg_backend_pid()")
        assert count == 0
    finally:
        await connection.close()
    output = await asyncio.to_thread(sandbox.command, "python3", "-c", "from pathlib import Path; print(sum(p.read_text().strip() == 'tail' and p.with_name('stat').read_text().split()[2] != 'Z' for p in Path('/proc').glob('[0-9]*/comm'))) ")
    assert output.strip() == "0"
