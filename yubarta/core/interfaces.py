from typing import Any, Protocol

from yubarta.core.models import Alert


class AlarmStorageInterface(Protocol):
    async def add(self, alert: Alert) -> Alert: ...

    async def get_all(self) -> list[Alert]: ...


class AlarmMessagingInterface(Protocol):
    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    async def publish(self, *, topic: str, value: Any, key: str | None = None) -> None: ...
