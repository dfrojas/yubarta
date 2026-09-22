import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import asyncssh

from yubarta.config.settings import Target
from yubarta.core.models import ExecutionResult


async def read_excerpt(reader: asyncssh.SSHReader[str]) -> str:
    chunks = []
    remaining = 8192
    while chunk := await reader.read(4096):
        if remaining:
            chunks.append(chunk[:remaining])
            remaining = max(0, remaining - len(chunk))
    return "".join(chunks)


async def close_process(connection: asyncssh.SSHClientConnection, process: asyncssh.SSHClientProcess[str]) -> None:
    try:
        if process.exit_status is None:
            process.terminate()
        async with asyncio.timeout(0.5):
            await process.wait_closed()
    except TimeoutError:
        process.close()
    finally:
        # Do not wait indefinitely for a peer which ignores channel close or TERM.
        connection.close()


class SSH:
    def __init__(self, target: Target):
        self.target = target
        self.connections: set[asyncssh.SSHClientConnection] = set()

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[asyncssh.SSHClientConnection]:
        target = self.target
        async with asyncssh.connect(
            target.host, port=target.port, username=target.user,
            client_keys=[str(Path(target.key).expanduser())],
            known_hosts=str(Path(target.known_hosts).expanduser()) if target.known_hosts else None,
            connect_timeout=target.connect_timeout,
            keepalive_interval=target.keepalive_interval, keepalive_count_max=target.keepalive_count_max,
        ) as connection:
            self.connections.add(connection)
            try:
                yield connection
            finally:
                self.connections.discard(connection)

    @asynccontextmanager
    async def stream(self, command: str) -> AsyncIterator[asyncssh.SSHClientProcess[str]]:
        async with self.connect() as connection:
            async with connection.create_process(command) as process:
                stderr_task = asyncio.create_task(read_excerpt(process.stderr))
                try:
                    yield process
                finally:
                    await close_process(connection, process)
                    stderr_task.cancel()
                    await asyncio.gather(stderr_task, return_exceptions=True)

    async def run(self, command: str, timeout: float) -> ExecutionResult:
        try:
            async with asyncio.timeout(timeout):
                async with self.connect() as connection:
                    async with connection.create_process(command) as process:
                        try:
                            stdout, stderr = await asyncio.gather(read_excerpt(process.stdout), read_excerpt(process.stderr))
                            await process.wait_closed()
                            return ExecutionResult(exit_code=process.exit_status, stdout=stdout, stderr=stderr,
                                                   passed=process.exit_status == 0)
                        finally:
                            await close_process(connection, process)
        except TimeoutError:
            return ExecutionResult(timed_out=True, error="SSH operation timed out")
        except (asyncssh.Error, OSError) as error:
            return ExecutionResult(error=f"SSH {type(error).__name__}: {error}")

    async def close(self) -> None:
        connections = list(self.connections)
        for connection in connections:
            connection.close()
        await asyncio.gather(*(connection.wait_closed() for connection in connections))
