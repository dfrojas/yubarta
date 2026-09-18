"""Scanner base contracts."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable

from yubarta.events.models import NormalizedEvent

EventHandler = Callable[[NormalizedEvent], Awaitable[None]]


@dataclass
class ScannerStatus:
    name: str
    kind: str
    target: str
    connected: bool = False
    last_event_at: str | None = None
    reconnect_count: int = 0
    last_error: str | None = None
    running: bool = False


@dataclass
class ReconnectPolicy:
    initial_delay: float = 1.0
    max_delay: float = 30.0
    factor: float = 2.0

    def delay_for(self, attempt: int) -> float:
        delay = self.initial_delay * (self.factor ** max(0, attempt - 1))
        return min(delay, self.max_delay)


class BaseScanner:
    def __init__(self, name: str, kind: str, target: str) -> None:
        self._status = ScannerStatus(name=name, kind=kind, target=target)
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()

    @property
    def status(self) -> ScannerStatus:
        return self._status

    async def start(self, handler: EventHandler) -> None:
        self._stop.clear()
        self._status.running = True
        self._task = asyncio.create_task(self._run(handler))

    async def stop(self) -> None:
        self._stop.set()
        self._status.running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None

    async def _run(self, handler: EventHandler) -> None:
        raise NotImplementedError

    def _note_event(self) -> None:
        import datetime

        self._status.last_event_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    def _note_error(self, message: str) -> None:
        self._status.last_error = message
        self._status.connected = False

    def _note_connected(self) -> None:
        self._status.connected = True
        self._status.last_error = None
