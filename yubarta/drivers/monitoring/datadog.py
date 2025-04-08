from datetime import datetime
import uuid
from yubarta.core.models import Alert
from yubarta.core.enums import AlertSource, AlertStatus


class DatadogHandler:
    def __init__(self, alarm: dict, fingerprint: str, received_at: str):
        self.alarm = alarm
        self.fingerprint = fingerprint
        self.received_at = received_at

    def process(self) -> Alert:
        return Alert(
            source=AlertSource.DATADOG,
            severity=self.alarm.get("alert_type", "info"),
            labels={
                "host": self.alarm.get("host", "unknown"),
                "org_id": self.alarm.get("org_id", ""),
                "tags": self.alarm.get("tags", []),
            },
            raw=self.alarm,
            status=AlertStatus.PENDING,
            received_at=self.received_at,
            status_updated_at=self.received_at,
            fingerprint=self.fingerprint
        )
