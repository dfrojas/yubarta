"""AsyncSSH execution connections (on-demand, closed after operations)."""

from __future__ import annotations

import dataclasses
from typing import Protocol

import asyncssh

from yubarta.config import TargetConfig


@dataclasses.dataclass
class CommandResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str


class SSHConnectionFactory(Protocol):
    async def run(self, command: str, timeout: float = 60.0) -> CommandResult: ...


class AsyncSSHExecutor:
    """Open an independent AsyncSSH connection per operation, close afterwards."""

    def __init__(self, target: TargetConfig) -> None:
        self._target = target

    def _connect_kwargs(self) -> dict:
        kwargs: dict = {
            "host": self._target.host,
            "port": self._target.port,
            "username": self._target.user,
            "client_keys": [self._target.key] if self._target.key else None,
            "password": self._target.password(),
            "known_hosts": None,
        }
        return kwargs

    async def run(self, command: str, timeout: float = 60.0) -> CommandResult:
        try:
            async with asyncssh.connect(**self._connect_kwargs()) as conn:
                result = await asyncio_wait(conn.run(command, timeout=timeout))
                return CommandResult(
                    command=command,
                    exit_code=result.exit_status if result.exit_status is not None else 1,
                    stdout=result.stdout if isinstance(result.stdout, str) else "",
                    stderr=result.stderr if isinstance(result.stderr, str) else "",
                )
        except asyncssh.Error as exc:
            raise ConnectionError(f"SSH execution failed for '{command}': {exc}") from exc


async def asyncio_wait(awaitable):  # type: ignore[no-untyped-def]
    return await awaitable
