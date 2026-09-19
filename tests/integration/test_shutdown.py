"""Integration: runtime shutdown cancels scanners and closes SSH and DB."""

from __future__ import annotations

import asyncio

from tests.integration.fake_ssh import FakeTargetState, start_fake_ssh_server
from yubarta.config import AppConfig, LogWatch, TargetConfig
from yubarta.runtime import YubartaRuntime


async def test_graceful_shutdown(test_db: str) -> None:
    state = FakeTargetState(healthy=True)
    listener, ssh_port = await start_fake_ssh_server(state)
    try:
        config = AppConfig(
            target=TargetConfig(host="127.0.0.1", user="tester", key="", port=ssh_port),
            watch=[LogWatch(file="/var/log/apache2/error.log", match_any=["AH00957"])],
        )
        runtime = YubartaRuntime(config, apply=False, database_url=test_db)
        await runtime.setup()
        await runtime.start_scanners()
        await asyncio.sleep(0.5)
        await asyncio.wait_for(runtime.shutdown(), timeout=15.0)
        assert all(not scanner.status.running for scanner in runtime.supervisor.scanners)
        assert runtime.db_healthy is False
    finally:
        listener.close()
        await listener.wait_closed()
