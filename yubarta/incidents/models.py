"""Pydantic domain models for incidents (persistence models stay separate)."""

from __future__ import annotations

import enum
from datetime import datetime

from pydantic import BaseModel, Field

from yubarta.incidents.state_machine import IncidentState


class StepKind(str, enum.Enum):
    DIAGNOSTIC = "diagnostic"
    PRECHECK = "precheck"
    REMEDIATION = "remediation"
    VERIFICATION = "verification"


class StepState(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    SKIPPED = "SKIPPED"


class Incident(BaseModel):
    id: str
    target: str
    incident_type: str
    state: IncidentState
    version: int = 0
    opened_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None
    resolved_by_step_id: str | None = None
    failure_reason: str | None = None


class IncidentStep(BaseModel):
    id: str
    incident_id: str
    sequence: int
    kind: StepKind
    name: str
    state: StepState = StepState.PENDING
    started_at: datetime | None = None
    finished_at: datetime | None = None
    exit_code: int | None = None
    stdout_excerpt: str | None = None
    stderr_excerpt: str | None = None
    result: dict = Field(default_factory=dict)
    error: str | None = None


class TriggerEvent(BaseModel):
    id: str
    incident_id: str
    source: str
    fingerprint: str
    observed_at: datetime
    raw: str
    fields: dict = Field(default_factory=dict)


class StateTransition(BaseModel):
    id: str
    incident_id: str
    from_state: IncidentState
    to_state: IncidentState
    created_at: datetime
    reason: str = ""
