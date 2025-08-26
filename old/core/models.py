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


# @dataclass
# class Remediation:
#     """
#     Domain model for remediation configurations stored in the system.
#     """
#     name: str
#     description: Optional[str] = None
#     version: str = "1.0"
#     created_at: datetime
#     updated_at: datetime
#     tags: list[str] = field(default_factory=list)
#     approval_required: bool = False
#     auto_approve_if_ai_generated: bool = False

#     # JSON blob fields to store complex configuration parts
#     match_details: dict[str, Any] = field(default_factory=dict)
#     targets_details: dict[str, Any] = field(default_factory=dict)
#     connection_details: dict[str, Any] = field(default_factory=dict)
#     execute_details: dict[str, Any] = field(default_factory=dict)
#     success_criteria_details: dict[str, Any] = field(default_factory=dict)
#     ai_details: dict[str, Any] = field(default_factory=dict)
#     telemetry_details: dict[str, Any] = field(default_factory=dict)
#     policy_details: dict[str, Any] = field(default_factory=dict)

#     def __post_init__(self) -> None:
#         # Ensure timestamps are timezone-aware (UTC) if they are naive
#         # TODO: Remember to add test for this case.
#         if self.created_at and self.created_at.tzinfo is None:
#             self.created_at = self.created_at.replace(tzinfo=datetime.timezone.utc)
#         if self.updated_at and self.updated_at.tzinfo is None:
#             self.updated_at = self.updated_at.replace(tzinfo=datetime.timezone.utc)

#     def update_timestamp(self) -> None:
#         self.updated_at = datetime.now(datetime.timezone.utc)
