"""Integration: SSH reconnection with backfill, exactly-once incident."""

from __future__ import annotations

import asyncio

from tests.integration.fake_ssh import (
    FakeTargetState,
    disconnect_all,
    start_fake_ssh_server,
)
from yubarta.config import AppConfig, LogWatch, TargetConfig
from yubarta.diagnostics.runner import DiagnosticsRunner
from yubarta.events.models import NormalizedEvent
from yubarta.execution.ssh import AsyncSSHExecutor
from yubarta.incidents.service import IncidentService
from yubarta.persistence.repository import IncidentRepository
from yubarta.persistence.session import create_engine, create_session_factory, init_db
from yubarta.rules.engine import RuleEngine
from yubarta.scanners.remote_file import RemoteFileScanner


async def test_ssh_reconnect_backfill_exactly_once(test_db: str) -> None:
    state = FakeTargetState(healthy=False)
    listener, ssh_port = await start_fake_ssh_server(state)
    engine = None
    scanner = None
    try:
        url = test_db
        engine = create_engine(url)
        await init_db(engine)
        sessions = create_session_factory(engine)
        config = AppConfig(
            target=TargetConfig(host="127.0.0.1", user="tester", key="", port=ssh_port),
            watch=[LogWatch(file="/var/log/apache2/error.log", match_any=["AH00957"])],
        )
        executor = AsyncSSHExecutor(config.target)
        service = IncidentService(
            config,
            sessions,
            RuleEngine.from_watches(config.watch),
            executor,
            DiagnosticsRunner(executor, config.diagnostics),
            apply=False,
        )
        received: list[NormalizedEvent] = []

        async def handler(event: NormalizedEvent) -> None:
            received.append(event)
            await service.handle_event(event)

        scanner = RemoteFileScanner(
            name="reconnect", target=config.target, watch=config.watch[0]
        )  # type: ignore[arg-type]
        await scanner.start(handler)
        await asyncio.sleep(1.0)
        assert scanner.status.connected

        # terminate the scanner SSH connection (keep listener up so reconnect is fast)
        disconnect_all(state)
        await asyncio.sleep(0.5)
        # emit matching event while disconnected: only the in-memory log grows
        state.append_log("AH00957: AJP Connection refused while scanner disconnected")
        # wait for automatic reconnect + backfill to retrieve the missed event
        for _ in range(300):
            if received:
                break
            await asyncio.sleep(0.1)
        assert received, "backfill did not retrieve the missed event"
        # no duplicate trigger event / no duplicate active incident
        async with sessions() as session:
            repo = IncidentRepository(session)
            incidents = await repo.list_incidents()
            assert len(incidents) == 1
            events = await repo.list_trigger_events(incidents[0].id)
            assert len(events) == 1
        assert scanner.status.reconnect_count >= 1
    finally:
        if scanner is not None:
            await scanner.stop()
        disconnect_all(state)
        listener.close()
        try:
            await asyncio.wait_for(listener.wait_closed(), timeout=10.0)
        except asyncio.TimeoutError:
            pass
        if engine is not None:
            await engine.dispose()
