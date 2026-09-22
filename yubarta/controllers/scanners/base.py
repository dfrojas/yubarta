import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from yubarta.controllers.scanners.contracts import EventHandler, ScannerStatus


@dataclass(frozen=True)
class ReconnectPolicy:
    initial_delay: float = 1.0
    max_delay: float = 30.0
    factor: float = 2.0

    def delay_for(self, attempt: int) -> float:
        delay = self.initial_delay
        for _ in range(max(0, attempt - 1)):
            delay = min(self.max_delay, delay * self.factor)
            if delay >= self.max_delay:
                break
        return min(self.max_delay, delay)


class BaseScanner(ABC):
    def __init__(self, name: str, kind: str, target: str) -> None:
        self._status = ScannerStatus(name=name, kind=kind, target=target)
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()
        self._logger = logging.getLogger(__name__)

    @property
    def status(self) -> ScannerStatus:
        return self._status

    async def start(self, handler: EventHandler) -> None:
        if self._task is not None and not self._task.done():
            raise RuntimeError(f"Scanner {self.status.name} is already running")
        self._stop.clear()
        self._status = replace(self._status, running=True)
        self._task = asyncio.create_task(self._observe(handler), name=self.status.name)

    async def _observe(self, handler: EventHandler) -> None:
        try:
            await self._run(handler)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._status = replace(self._status, last_error=str(exc))
            self._logger.exception("Scanner %s stopped unexpectedly", self.status.name)
        finally:
            self._status = replace(self._status, running=False, connected=False)

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                # The child cancellation is expected; caller cancellation is not.
                current = asyncio.current_task()
                if current is not None and current.cancelling():
                    raise
            finally:
                self._task = None
        self._status = replace(self._status, running=False, connected=False)

    @abstractmethod
    async def _run(self, handler: EventHandler) -> None: ...

    async def _wait(self, delay: float) -> None:
        try:
            await asyncio.wait_for(self._stop.wait(), timeout=delay)
        except TimeoutError:
            return

    def _note_event(self) -> None:
        self._status = replace(self._status, last_event_at=datetime.now(UTC))

    def _note_error(self, error: Exception) -> None:
        self._status = replace(
            self._status,
            connected=False,
            last_error=str(error),
            reconnect_count=self._status.reconnect_count + 1,
        )

    def _note_connected(self) -> None:
        self._status = replace(self._status, connected=True, last_error=None)
