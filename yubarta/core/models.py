"""Pydantic domain models for incidents (persistence models stay separate)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from yubarta.core.enums import IncidentState, StepKind, StepState


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
    from_state: str
    to_state: IncidentState
    created_at: datetime
    reason: str = ""


class NormalizedEvent(BaseModel):
    source: str
    target: str
    observed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    message: str
    raw: str
    event_at: datetime | None = None
    level: str | None = None
    fields: dict[str, Any] = Field(default_factory=dict)

    def fingerprint(self) -> str:
        basis = f"{self.source}|{self.target}|{self.message}|{self.raw}"
        return hashlib.sha256(basis.encode()).hexdigest()[:32]


@dataclass(frozen=True)
class CommandResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class CheckOutcome:
    name: str
    passed: bool
    detail: str
    exit_code: int | None = None
    status: int | None = None


@dataclass(frozen=True)
class IncidentDetail:
    incident: Incident
    steps: list[IncidentStep]
    transitions: list[StateTransition]
