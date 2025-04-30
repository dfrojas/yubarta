from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from yubarta.core.enums import AlertSeverity, AlertSource, AlertStatus
from yubarta.core.models import Alert


class AlertRequest(BaseModel):
    """
    This schema is optional since we're identifying the provider from the raw payload.
    It could be used for documentation purposes or for APIs where the source is known.
    """

    source: AlertSource
    severity: AlertSeverity
    status: AlertStatus

    def to_domain(self, received_at: datetime) -> Alert:
        return Alert(
            source=self.source,
            severity=self.severity,
            status=self.status,
            received_at=received_at,
        )


class AlertResponse(BaseModel):
    """
    A lightweight response returned immediately when an alert is received.
    This allows for fast response times while processing continues asynchronously.
    """

    alert_id: str
    status: str
    received_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        orm_mode = True


class AlertKafkaMessage(BaseModel):
    source: str
    severity: str
    status: str
    received_at: datetime
    fingerprint: Optional[str] = None

    class Config:
        orm_mode = True

    @classmethod
    def from_domain(cls, alert: "Alert") -> "AlertKafkaMessage":
        return cls(
            source=alert.source,
            severity=alert.severity,
            status=alert.status,
            received_at=alert.received_at,
            fingerprint=alert.fingerprint,
        )
