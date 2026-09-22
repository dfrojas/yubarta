"""Integration: SSH reconnection with backfill, exactly-once incident."""

from __future__ import annotations

import asyncio
from functools import partial

import httpx

from tests.integration.fake_ssh import (
    FakeTargetState,
    close_fake_ssh_server,
    disconnect_all,
    start_fake_ssh_server,
)
from yubarta.config.settings import AppConfig, LogWatch, TargetConfig
from yubarta.controllers.checks import ChecksRunner
from yubarta.controllers.diagnostics import DiagnosticsRunner
from yubarta.controllers.incidents import IncidentService
from yubarta.controllers.remediations.runner import RemediationRunner
from yubarta.controllers.scanners.remote_file import RemoteFileScanner
from yubarta.core.models import NormalizedEvent
from yubarta.core.rules import RuleEngine
from yubarta.drivers.db.initialization import init_db
from yubarta.drivers.db.repository import SqlAlchemyIncidentRepository as IncidentRepository
from yubarta.drivers.db.sessions import create_engine, create_session_factory
from yubarta.drivers.db.sqlalchemy import SqlAlchemyUnitOfWork
from yubarta.drivers.network.files import SSHFileSource
from yubarta.drivers.network.http import HttpChecks
from yubarta.drivers.network.ssh import AsyncSSHExecutor


async def test_ssh_reconnect_backfill_exactly_once(test_db: str) -> None:
    state = FakeTargetState(healthy=False)
    listener, ssh_port = await start_fake_ssh_server(state)
    engine = None
    scanner = None
    http_client = httpx.AsyncClient()
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
            partial(SqlAlchemyUnitOfWork, sessions),
            RuleEngine.from_watches(config.watch),
            DiagnosticsRunner(executor, config.diagnostics),
            ChecksRunner(config.checks, executor, HttpChecks(http_client)),
            RemediationRunner(executor, apply=False),
        )
        received: list[NormalizedEvent] = []

        async def handler(event: NormalizedEvent) -> None:
            received.append(event)
            await service.handle_event(event)

        scanner = RemoteFileScanner(
            name="reconnect", target=config.target.host, watch=config.watch[0], source=SSHFileSource(config.target)
        )
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
        await http_client.aclose()
        if scanner is not None:
            await scanner.stop()
        await close_fake_ssh_server(listener, state)
        if engine is not None:
            await engine.dispose()
