"""Integration: runtime shutdown cancels scanners and closes SSH and DB."""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine

from tests.integration.fake_ssh import FakeTargetState, close_fake_ssh_server, start_fake_ssh_server
from yubarta import runtime as runtime_module
from yubarta.config.settings import AppConfig, LogWatch, TargetConfig
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
        await close_fake_ssh_server(listener, state)


async def test_partial_startup_closes_resources_and_allows_retry(test_db: str, monkeypatch: pytest.MonkeyPatch) -> None:
    disposed: list[bool] = []
    clients = []
    create_engine = runtime_module.create_engine

    def tracked_engine(url: str, **options: object) -> AsyncEngine:
        engine = create_engine(url, **options)
        event.listen(engine.sync_engine, "engine_disposed", lambda _: disposed.append(True))
        return engine

    def fail_construction() -> None:
        clients.append(runtime._http_client)
        raise RuntimeError("construction failed")

    config = AppConfig(target=TargetConfig(host="vm", user="operator"))
    runtime = YubartaRuntime(config, database_url=test_db)
    with monkeypatch.context() as patch:
        patch.setattr(runtime_module, "create_engine", tracked_engine)
        patch.setattr(runtime, "_build_services", fail_construction)
        with pytest.raises(RuntimeError, match="construction failed"):
            await runtime.setup()
    assert disposed == [True]
    assert clients[0] is not None and clients[0].is_closed
    assert not runtime.db_healthy
    with pytest.raises(RuntimeError, match="not set up"):
        _ = runtime.services
    try:
        await runtime.setup()
        assert runtime.db_healthy
    finally:
        await runtime.shutdown()
    await runtime.shutdown()
