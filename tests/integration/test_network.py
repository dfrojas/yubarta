import asyncio
from time import monotonic

import pytest

from tests.support import Sandbox
from yubarta.config.settings import AppConfig, CommandWatch, LogWatch, ParserConfig
from yubarta.controllers.scanners.remote_command import RemoteCommandScanner
from yubarta.controllers.scanners.remote_file import RemoteFileScanner
from yubarta.core.models import NormalizedEvent
from yubarta.drivers.network.files import RemoteFileSource
from yubarta.drivers.network.ssh import SSH

pytestmark = pytest.mark.integration


async def test_ssh_exit_timeout_output_and_independent_sessions(ssh: SSH) -> None:
    result = await ssh.run("printf diagnostic; printf error >&2; exit 7", 5)
    assert result.exit_code == 7 and result.stdout == "diagnostic" and result.stderr == "error"
    assert not result.passed
    started = monotonic()
    assert (await ssh.run("sleep 5", 0.5)).timed_out
    assert monotonic() - started < 2
    result = await ssh.run("python3 -c 'print(\"x\" * 100000)'", 5)
    assert result.passed and len(result.stdout) == 8192
    async with ssh.stream("tail -F /var/log/apache2/error.log"):
        assert (await ssh.run("printf independent", 5)).stdout == "independent"
    assert not ssh.connections


async def test_idle_stream_shutdown_is_bounded(ssh: SSH, product_config: AppConfig) -> None:
    async def collect(event: NormalizedEvent, watch: object) -> None:
        raise AssertionError("Idle command emitted an event")

    scanner = RemoteCommandScanner(CommandWatch(name="idle", run="sleep 60"), product_config.target.host, collect, ssh)
    scanner.start()
    try:
        for _ in range(100):
            if scanner.status.state == "connected":
                break
            await asyncio.sleep(0.02)
        assert scanner.status.state == "connected"
        await asyncio.wait_for(scanner.stop(), timeout=2)
        assert not ssh.connections
    finally:
        await ssh.close()


async def test_swap_script_preserves_existing_data(ssh: SSH, sandbox: Sandbox) -> None:
    await asyncio.to_thread(sandbox.reset)
    await asyncio.to_thread(sandbox.command, "python3", "-c",
                            "with open('/swapfile-yubarta','wb') as f: f.write(b'preserve me'); f.truncate(2147483648)")
    result = await ssh.run("sudo -n /opt/yubarta/ensure-swap", 10)
    assert not result.passed
    contents = await asyncio.to_thread(sandbox.command, "python3", "-c",
                                       "with open('/swapfile-yubarta','rb') as f: print(f.read(11).decode())")
    assert contents.strip() == "preserve me"


async def test_file_backfill_live_stream_and_command_modes(ssh: SSH, product_config: AppConfig, sandbox: Sandbox) -> None:
    await asyncio.to_thread(sandbox.reset)
    await asyncio.to_thread(sandbox.command, "python3", "-c", "from pathlib import Path; Path('/var/log/apache2/error.log').write_text('backfill\\n')")
    events: asyncio.Queue[NormalizedEvent] = asyncio.Queue()

    async def collect(event: NormalizedEvent, watch: object) -> None:
        await events.put(event)

    watch = LogWatch(name="file", file="/var/log/apache2/error.log")
    scanner = RemoteFileScanner(watch, product_config.target.host, collect, RemoteFileSource(ssh, watch))
    scanner.start()
    try:
        assert (await asyncio.wait_for(events.get(), 5)).raw == "backfill"
        await asyncio.to_thread(sandbox.command, "python3", "-c", "with open('/var/log/apache2/error.log','a') as f: f.write('live\\n')")
        assert (await asyncio.wait_for(events.get(), 5)).raw == "live"
    finally:
        await scanner.stop()
    assert scanner.task.done() and not ssh.connections
    for interval in [None, 0.1]:
        watch = CommandWatch(name="command", run="printf '{\"message\":\"command event\",\"level\":\"INFO\"}\\n'; sleep 0.1",
                             interval=interval, parser=ParserConfig(kind="json"))
        scanner = RemoteCommandScanner(watch, product_config.target.host, collect, ssh)
        scanner.start()
        try:
            event = await asyncio.wait_for(events.get(), 5)
            assert event.message.strip() == "command event"
            assert event.level == "INFO"
            if interval:
                assert event.fields["exit_code"] == 0
        finally:
            await scanner.stop()
    assert not ssh.connections
