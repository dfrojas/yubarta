from datetime import datetime
import uuid
from yubarta.core.models import Alert
from yubarta.core.enums import AlertSource, AlertStatus


class DatadogHandler:
    def __init__(self, alarm: dict):
        self.alarm = alarm

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
            received_at=datetime.utcnow(),
            status_updated_at=datetime.utcnow(),
            fingerprint=self._generate_fingerprint()
        )

    def _generate_fingerprint(self) -> str:
        # In a real implementation, this would create a unique fingerprint based on alert attributes
        # to help with deduplication
        alert_id = self.alarm.get("alert_id", "")
        return f"datadog:{alert_id}" if alert_id else str(uuid.uuid4())
