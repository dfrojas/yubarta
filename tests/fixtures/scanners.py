from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest

from yubarta.core.models import CommandResult


class CommandSource:
    def __init__(self) -> None:
        self.connected = asyncio.Event()
        self.closed = asyncio.Event()
        self.connections = 0
        self.commands: list[str] = []
        self.fail_next = False

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[CommandSource]:
        self.connections += 1
        self.connected.set()
        try:
            yield self
        finally:
            self.closed.set()

    async def run(self, command: str, timeout: float = 60.0) -> CommandResult:
        self.commands.append(command)
        if self.fail_next:
            self.fail_next = False
            raise ConnectionError("connection lost")
        return CommandResult(command, 3, "inactive", "")


class FileSource:
    def __init__(self) -> None:
        self.lines: asyncio.Queue[str] = asyncio.Queue()
        self.closed = asyncio.Event()
        self.requests: list[tuple[str, int]] = []

    @asynccontextmanager
    async def follow(self, path: str, backfill_lines: int) -> AsyncIterator[AsyncIterator[str]]:
        self.requests.append((path, backfill_lines))
        try:
            yield self._lines()
        finally:
            self.closed.set()

    async def _lines(self) -> AsyncIterator[str]:
        while True:
            yield await self.lines.get()


@pytest.fixture
def command_source() -> CommandSource:
    return CommandSource()


@pytest.fixture
def file_source() -> FileSource:
    return FileSource()
