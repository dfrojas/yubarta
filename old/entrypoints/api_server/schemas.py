from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from yubarta.core.enums import AlertSeverity, AlertSource, AlertStatus
from yubarta.core.models import Alert


class AlertRequest(BaseModel):
    external_id: str
    source: AlertSource
    title: str
    message: str
    status: AlertStatus
    severity: AlertSeverity
    scope: Optional[str] = None
    tags: list[str] = []
    occurred_at: datetime
    enriched: Optional[bool] = False
    raw_payload: Optional[dict[str, Any]] = {}

    def to_domain(self, received_at: datetime) -> Alert:
        return Alert(
            external_id=self.external_id,
            source=self.source,
            title=self.title,
            message=self.message,
            status=self.status,
            severity=self.severity,
            scope=self.scope,
            tags=self.tags,
            occurred_at=self.occurred_at,
            received_at=received_at,
            enriched=bool(self.enriched),
            raw_payload=self.raw_payload or {},
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
        from_attributes = True


class AlertKafkaMessage(BaseModel):
    external_id: str
    source: AlertSource
    title: str
    message: str
    status: AlertStatus
    severity: AlertSeverity
    scope: Optional[str] = None
    tags: list[str] = []
    occurred_at: datetime
    enriched: bool
    raw_payload: Optional[dict[str, Any]] = {}
    fingerprint: str
    received_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_domain(cls, alert: "Alert") -> "AlertKafkaMessage":
        return cls(
            external_id=alert.external_id,
            source=alert.source,
            title=alert.title,
            message=alert.message,
            status=alert.status,
            severity=alert.severity,
            scope=alert.scope,
            tags=alert.tags,
            occurred_at=alert.occurred_at,
            received_at=alert.received_at,
            fingerprint=alert.fingerprint,
            enriched=alert.enriched,
            raw_payload=alert.raw_payload,
        )

    def to_domain(self) -> Alert:
        return Alert(
            external_id=self.external_id,
            source=self.source,
            title=self.title,
            message=self.message,
            status=self.status,
            severity=self.severity,
            scope=self.scope,
            tags=self.tags,
            occurred_at=self.occurred_at,
            received_at=self.received_at,
            enriched=bool(self.enriched),
            raw_payload=self.raw_payload or {},
        )
