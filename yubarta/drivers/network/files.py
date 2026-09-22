import asyncio
import shlex
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncssh

from yubarta.config.settings import TargetConfig
from yubarta.drivers.network.ssh import connection_options


class SSHFileSource:
    def __init__(self, target: TargetConfig) -> None:
        self._target = target

    @asynccontextmanager
    async def follow(self, path: str, backfill_lines: int) -> AsyncIterator[AsyncIterator[str]]:
        # One tail process avoids a gap between backfill and live observation.
        command = f"tail -n {backfill_lines} -F {shlex.quote(path)}"
        try:
            async with asyncssh.connect(**connection_options(self._target)) as connection:
                process = await connection.create_process(command)
                try:
                    yield self._lines(process)
                finally:
                    process.terminate()
                    process.close()
                    await asyncio.wait_for(process.wait_closed(), timeout=5.0)
        except (asyncssh.Error, OSError) as exc:
            raise ConnectionError(f"SSH file observation failed for {path}: {exc}") from exc

    async def _lines(self, process: asyncssh.SSHClientProcess) -> AsyncIterator[str]:
        async for line in process.stdout:
            yield line.rstrip("\n")
