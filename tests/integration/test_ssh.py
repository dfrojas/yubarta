"""Integration: AsyncSSH against in-process sandbox (remote commands + file streaming)."""

from __future__ import annotations

from tests.integration.fake_ssh import FakeTargetState
from yubarta.config import CommandWatch, LogWatch, TargetConfig
from yubarta.events.models import NormalizedEvent
from yubarta.execution.ssh import AsyncSSHExecutor
from yubarta.scanners.remote_command import RemoteCommandScanner
from yubarta.scanners.remote_file import RemoteFileScanner


def _target(port: int) -> TargetConfig:
    return TargetConfig(host="127.0.0.1", user="tester", key="", port=port)


async def test_remote_command_execution(
    ssh_target: tuple[FakeTargetState, int],
) -> None:
    state, port = ssh_target
    executor = AsyncSSHExecutor(_target(port))
    result = await executor.run("uptime", timeout=10.0)
    assert result.exit_code == 0
    state.healthy = False
    failed = await executor.run("sudo -n systemctl is-active --quiet tomcat9", timeout=10.0)
    assert failed.exit_code == 3


async def test_remote_file_streaming_backfill(
    ssh_target: tuple[FakeTargetState, int],
) -> None:
    state, port = ssh_target
    received: list[NormalizedEvent] = []

    async def handler(event: NormalizedEvent) -> None:
        received.append(event)

    watch = LogWatch(file="/var/log/apache2/error.log", match_any=["AH00957"])
    scanner = RemoteFileScanner(name="t", target=_target(port), watch=watch)
    state.append_log("AH00957: AJP Connection refused")
    await scanner.start(handler)
    try:
        import asyncio

        for _ in range(100):
            if received:
                break
            await asyncio.sleep(0.05)
    finally:
        await scanner.stop()
    assert received and "AH00957" in received[0].message


async def test_command_scanner_detects_failure(
    ssh_target: tuple[FakeTargetState, int],
) -> None:
    state, port = ssh_target
    received: list[NormalizedEvent] = []

    async def handler(event: NormalizedEvent) -> None:
        received.append(event)

    state.healthy = False
    watch = CommandWatch(run="sudo -n systemctl is-active --quiet tomcat9", interval="100ms")
    scanner = RemoteCommandScanner(name="c", target=_target(port), watch=watch)
    await scanner.start(handler)
    try:
        import asyncio

        for _ in range(100):
            if received:
                break
            await asyncio.sleep(0.05)
    finally:
        await scanner.stop()
    assert received and received[0].fields.get("check_failed") is True
