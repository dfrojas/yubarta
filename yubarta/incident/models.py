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


class IncidentTransition(BaseModel):
    """One entry of the append-only lifecycle log.

    Readable, not just writable: the log is what a restarted process folds to learn
    what actually happened, so a store that only appends to it would make crash
    recovery unverifiable.
    """

    id: str
    incident_id: str
    from_state: IncidentState
    to_state: IncidentState
    occurred_at: datetime


class Incident(BaseModel):
    """One Signal-driven remediation lifecycle.

    `version` and `lease_generation` guard two different races and are never
    collapsed into one counter (ADR-0006). `version` moves on every transition
    and detects that the state changed under a caller. `lease_generation` moves
    only when the Director acquires the ownership lease and detects that
    ownership changed, which a correct `version` cannot reveal.
    """

    id: str
    signal: Signal
    target_name: str
    state: IncidentState
    version: int
    lease_owner: str | None
    lease_generation: int
    lease_expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
    attempts: list[RemediationAttempt]
