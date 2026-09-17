import hashlib
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, computed_field


class SignalStatus(StrEnum):
    firing = "firing"
    resolved = "resolved"


class SignalSource(StrEnum):
    webhook = "webhook"
    scanner = "scanner"
    chatops = "chatops"


class Signal(BaseModel):
    status: SignalStatus
    source: SignalSource
    labels: dict[str, str]
    fired_at: datetime
    raw: dict[str, Any]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def fingerprint(self) -> str:
        parts = sorted(f"{k}={v}" for k, v in self.labels.items())
        seed = "|".join([self.source, *parts])
        return hashlib.sha256(seed.encode()).hexdigest()[:16]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def id(self) -> str:
        seed = f"{self.fingerprint}|{self.fired_at.isoformat()}"
        return hashlib.sha256(seed.encode()).hexdigest()[:16]
