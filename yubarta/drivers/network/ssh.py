"""AsyncSSH execution connections (on-demand, closed after operations)."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncssh

from yubarta.config.settings import TargetConfig
from yubarta.core.models import CommandResult


def connection_options(target: TargetConfig) -> dict[str, object]:
    return {
        "host": target.host,
        "port": target.port,
        "username": target.user,
        "client_keys": [target.key] if target.key else None,
        "password": os.environ.get(target.password_from_env) if target.password_from_env else None,
        "known_hosts": target.known_hosts,
        "keepalive_interval": 15.0,
    }


class AsyncSSHExecutor:
    """Open an independent AsyncSSH connection per operation, close afterwards."""

    def __init__(self, target: TargetConfig) -> None:
        self._target = target

    async def run(self, command: str, timeout: float = 60.0) -> CommandResult:
        try:
            async with asyncssh.connect(**connection_options(self._target)) as conn:
                result = await conn.run(command, timeout=timeout)
                return CommandResult(
                    command=command,
                    exit_code=result.exit_status if result.exit_status is not None else 1,
                    stdout=result.stdout if isinstance(result.stdout, str) else "",
                    stderr=result.stderr if isinstance(result.stderr, str) else "",
                )
        except (asyncssh.Error, OSError) as exc:
            raise ConnectionError(f"SSH execution failed for '{command}': {exc}") from exc


class ConnectedCommandExecutor:
    def __init__(self, connection: asyncssh.SSHClientConnection) -> None:
        self._connection = connection

    async def run(self, command: str, timeout: float = 60.0) -> CommandResult:
        try:
            result = await self._connection.run(command, timeout=timeout)
        except (asyncssh.Error, OSError) as exc:
            raise ConnectionError(f"SSH execution failed for '{command}': {exc}") from exc
        return CommandResult(
            command,
            result.exit_status if result.exit_status is not None else 1,
            result.stdout if isinstance(result.stdout, str) else "",
            result.stderr if isinstance(result.stderr, str) else "",
        )


class SSHCommandSource:
    def __init__(self, target: TargetConfig) -> None:
        self._target = target

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[ConnectedCommandExecutor]:
        try:
            async with asyncssh.connect(**connection_options(self._target)) as connection:
                yield ConnectedCommandExecutor(connection)
        except (asyncssh.Error, OSError) as exc:
            raise ConnectionError(f"SSH connection failed: {exc}") from exc
