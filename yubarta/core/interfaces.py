from typing import Protocol, runtime_checkable

from yubarta.core.models import Alert


@runtime_checkable
class AlarmProviderInterface(Protocol):
    def configure(self, alarm: dict) -> Alert: ...

    def normalize(self, alarm: dict) -> Alert: ...

    def run(self, alarm: dict) -> Alert: ...


class AlarmStorageInterface(Protocol):
    def add(self, alert: Alert): ...

    def get(self, alert_id: str) -> Alert: ...

    def update(self, alert: Alert): ...


class AlarmMessagingInterface(Protocol):
    def publish(self, alert: Alert): ...
