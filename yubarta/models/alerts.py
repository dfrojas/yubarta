from datetime import datetime
import hashlib
from typing import Any
from pydantic import BaseModel, ConfigDict, computed_field, field_serializer


class AlertLabels(BaseModel):
    """Labels for alert metadata"""
    env: str
    team: str
    region: str


class Alert(BaseModel):
    """
    Alert model for normalized alert data.
    @TODO: Remember that this is the normalized alert data
    but I have fields specific to the source system in this model (e.g lag is Kafka)
    I need to find out how to handle this to have global model.
    """

    model_config = ConfigDict(extra="ignore")

    id: str
    source: str
    type: str
    severity: str
    service: str
    group_id: str
    topic: str
    lag: int
    window: str
    threshold: int
    fired_at: datetime
    labels: AlertLabels

    @field_serializer("fired_at")
    def serialize_fired_at(self, fired_at: datetime) -> str:
        return fired_at.isoformat()

    @computed_field
    @property
    def event_id(self) -> str:
        seed = f"{self.source}|{self.type}|{self.group_id}|{self.topic}|{self.fired_at.isoformat()}"
        return hashlib.sha256(seed.encode()).hexdigest()[:16]

    @computed_field
    @property
    def fingerprint(self) -> str:
        parts = [
            self.source,
            self.type,
            self.group_id,
            self.topic,
            self.labels.env,
            self.labels.region,
            self.severity,
        ]
        key = ":".join(p.lower() or "-" for p in parts)
        return hashlib.sha256(key.encode()).hexdigest()[:16]
