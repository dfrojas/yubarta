import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from yubarta.core.enums import AlertSeverity, AlertSource, AlertStatus


@dataclass
class Alert:
    """
    Domain model for system alerts, matching the required alert structure.
    """

    external_id: str
    source: AlertSource
    title: str
    message: str
    status: AlertStatus
    severity: AlertSeverity
    scope: Optional[str]
    tags: list[str]
    occurred_at: datetime
    received_at: datetime
    fingerprint: str = field(init=False)
    enriched: bool = False
    raw_payload: dict[str, Any] = field(default_factory=dict)

    def mark_acknowledged(self) -> None:
        self.status = AlertStatus.ACKNOWLEDGED

    def mark_resolved(self) -> None:
        self.status = AlertStatus.RESOLVED

    def add_tag(self, tag: str) -> None:
        if tag not in self.tags:
            self.tags.append(tag)

    def enrich(self, context: dict[str, Any]) -> None:
        self.enriched = True

    def __post_init__(self) -> None:
        if not self.fingerprint:  # TODO: Remember to add unit test of this.
            key_parts = [
                self.source.value,
                self.severity.value,
                self.scope or "",
                self.title.strip().lower(),
            ]
            raw_key = "|".join(key_parts)
            self.fingerprint = hashlib.sha256(raw_key.encode()).hexdigest()
