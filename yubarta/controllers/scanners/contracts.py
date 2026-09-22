from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from typing import Protocol

from yubarta.config.settings import Watch
from yubarta.core.models import NormalizedEvent, ScannerStatus
from yubarta.core.interfaces import CommandPort

type EventCallback = Callable[[NormalizedEvent, Watch], Awaitable[None]]


class LineReader(Protocol):
    async def readline(self) -> str: ...


class StreamProcess(Protocol):
    stdout: LineReader


class FileSource(Protocol):
    def open(self) -> AbstractAsyncContextManager[StreamProcess]: ...


class CommandSource(CommandPort, Protocol):
    def stream(self, command: str) -> AbstractAsyncContextManager[StreamProcess]: ...


class Scanner(Protocol):
    status: ScannerStatus

    def start(self) -> None: ...

    async def stop(self) -> None: ...
