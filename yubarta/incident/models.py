from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel

from yubarta.domain.signal import Signal


class IncidentState(StrEnum):
    received = "received"
    diagnosing = "diagnosing"
    remediating = "remediating"
    verifying = "verifying"
    escalated = "escalated"
    resolved = "resolved"


class AttemptOutcome(StrEnum):
    succeeded = "succeeded"
    failed = "failed"
    skipped = "skipped"


class AttemptApproval(StrEnum):
    not_required = "not_required"
    pending = "pending"
    approved = "approved"
    denied = "denied"


class RemediationAttempt(BaseModel):
    id: str
    incident_id: str
    remediation_name: str
    idempotency_key: str
    attempt_sequence: int
    approval_status: AttemptApproval
    approved_by: str | None
    approved_at: datetime | None
    started_at: datetime
    completed_at: datetime | None
    outcome: AttemptOutcome | None
    evidence: dict[str, Any] | None


class Incident(BaseModel):
    id: str
    signal: Signal
    target_name: str
    state: IncidentState
    created_at: datetime
    updated_at: datetime
    attempts: list[RemediationAttempt]
