from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from yubarta.core.interfaces import CommandExecutor
from yubarta.core.models import NormalizedEvent

EventHandler = Callable[[NormalizedEvent], Awaitable[None]]


@dataclass(frozen=True)
class ScannerStatus:
    name: str
    kind: str
    target: str
    running: bool = False
    connected: bool = False
    last_event_at: datetime | None = None
    last_error: str | None = None
    reconnect_count: int = 0


class Scanner(Protocol):
    @property
    def status(self) -> ScannerStatus: ...

    async def start(self, handler: EventHandler) -> None:
        """Start background observation and return without waiting for completion."""
        ...

    async def stop(self) -> None:
        """Stop observation and wait for owned resources to be released."""
        ...


class CommandSource(Protocol):
    def connect(self) -> AbstractAsyncContextManager[CommandExecutor]: ...


class FileSource(Protocol):
    def follow(self, path: str, backfill_lines: int) -> AbstractAsyncContextManager[AsyncIterator[str]]: ...
