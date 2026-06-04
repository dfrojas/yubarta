from typing import Protocol

from yubarta.domain.signal import Signal


class SignalStore(Protocol):
    async def add(self, signal: Signal) -> Signal: ...
    async def get(self, signal_id: str) -> Signal | None: ...


class MessageBus(Protocol):
    async def publish(self, topic: str, signal: Signal) -> None: ...


class RemoteExecutor(Protocol):
    async def exec(self, host: str, command: str) -> tuple[int, str, str]: ...
