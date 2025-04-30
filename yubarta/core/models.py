import hashlib
from dataclasses import dataclass, field
from datetime import datetime

from yubarta.core.enums import AlertSeverity, AlertSource, AlertStatus


@dataclass
class Alert:
    severity: AlertSeverity
    status: AlertStatus
    source: AlertSource
    received_at: datetime
    status_updated_at: datetime | None = None
    fingerprint: str = field(init=False)

    def __post_init__(self) -> None:
        raw = f"{self.source}-{self.severity}-{self.received_at.isoformat()}"
        self.fingerprint = hashlib.sha256(raw.encode()).hexdigest()
