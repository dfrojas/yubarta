import asyncio
from dataclasses import FrozenInstanceError

import pytest

from tests.fixtures.scanners import CommandSource, FileSource
from yubarta.config.settings import CommandWatch, LogWatch
from yubarta.controllers.scanners.base import ReconnectPolicy
from yubarta.controllers.scanners.remote_command import RemoteCommandScanner
from yubarta.controllers.scanners.remote_file import RemoteFileScanner
from yubarta.controllers.scanners.supervisor import ScannerSupervisor
from yubarta.core.models import NormalizedEvent


async def test_command_observation_uses_injected_source_and_closes_it(command_source: CommandSource) -> None:
    received: list[NormalizedEvent] = []
    observed = asyncio.Event()

    async def handler(event: NormalizedEvent) -> None:
        received.append(event)
        observed.set()

    scanner = RemoteCommandScanner("check", "vm", CommandWatch(run="health", interval=3600), command_source)
    supervisor = ScannerSupervisor([scanner])
    await asyncio.wait_for(supervisor.start(handler), timeout=1)
    try:
        await asyncio.wait_for(observed.wait(), timeout=1)
        assert command_source.commands == ["health"]
        assert received[0].fields["exit_code"] == 3
        status = supervisor.statuses()[0]
        assert status.connected and status.running
        with pytest.raises(FrozenInstanceError):
            status.running = False
        with pytest.raises(RuntimeError, match="already running"):
            await scanner.start(handler)
    finally:
        await asyncio.wait_for(supervisor.stop(), timeout=1)
    assert command_source.closed.is_set()
    assert not scanner.status.running and not scanner.status.connected
    await supervisor.stop()


async def test_command_observation_recovers_after_transport_failure(command_source: CommandSource) -> None:
    command_source.fail_next = True
    observed = asyncio.Event()

    async def handler(event: NormalizedEvent) -> None:
        observed.set()

    scanner = RemoteCommandScanner(
        "check",
        "vm",
        CommandWatch(run="health", interval=3600),
        command_source,
        reconnect=ReconnectPolicy(initial_delay=0.001),
    )
    await scanner.start(handler)
    try:
        await asyncio.wait_for(observed.wait(), timeout=1)
        assert command_source.connections == 2
        assert scanner.status.reconnect_count == 1
        assert scanner.status.last_error is None
    finally:
        await scanner.stop()


async def test_file_normalization_filtering_and_deduplication(file_source: FileSource) -> None:
    received: list[NormalizedEvent] = []
    finished = asyncio.Event()

    async def handler(event: NormalizedEvent) -> None:
        received.append(event)
        if event.message == "failure second":
            finished.set()

    for line in ("ignored", "failure first", "failure first", "failure second"):
        file_source.lines.put_nowait(line)
    scanner = RemoteFileScanner(
        "logs", "vm", LogWatch(file="/logs/app.log", match_any=["failure"], backfill_lines=20), file_source
    )
    await scanner.start(handler)
    try:
        await asyncio.wait_for(finished.wait(), timeout=1)
        assert [event.message for event in received] == ["failure first", "failure second"]
        assert all(event.target == "vm" and event.source == "log:/logs/app.log" for event in received)
        assert file_source.requests == [("/logs/app.log", 20)]
    finally:
        await asyncio.wait_for(scanner.stop(), timeout=1)
    assert file_source.closed.is_set()


async def test_stopping_scanner_cancels_inflight_handler_and_closes_source(command_source: CommandSource) -> None:
    entered = asyncio.Event()
    cancelled = asyncio.Event()

    async def handler(event: NormalizedEvent) -> None:
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    scanner = RemoteCommandScanner("check", "vm", CommandWatch(run="health"), command_source)
    await scanner.start(handler)
    try:
        await asyncio.wait_for(entered.wait(), timeout=1)
    finally:
        await asyncio.wait_for(scanner.stop(), timeout=1)
    assert cancelled.is_set() and command_source.closed.is_set()
