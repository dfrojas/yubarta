import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from yubarta.core.enums import IncidentState, StepKind, StepState


def utcnow() -> datetime:
    return datetime.now(UTC)


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)


class NormalizedEvent(Model):
    source: str
    target: str
    observed_at: datetime = Field(default_factory=utcnow)
    message: str
    raw: str
    event_timestamp: datetime | None = None
    level: str | None = None
    fields: dict[str, Any] = Field(default_factory=dict)

    def fingerprint(self) -> str:
        # ponytail: identical timestamp-free log lines deduplicate forever; add source IDs if needed.
        identity = [self.target, self.source, self.raw, self.fields.get("sample_id")]
        return hashlib.sha256(json.dumps(identity).encode()).hexdigest()


class ExecutionResult(Model):
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    error: str | None = None
    timed_out: bool = False
    passed: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class Incident(Model):
    id: UUID
    target: str
    incident_type: str
    state: IncidentState
    version: int
    opened_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None
    resolved_by_step_id: UUID | None = None
    failure_reason: str | None = None


class Step(Model):
    id: UUID
    incident_id: UUID
    sequence: int
    kind: StepKind
    name: str
    state: StepState
    started_at: datetime
    finished_at: datetime | None = None
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class Transition(Model):
    from_state: IncidentState | None
    to_state: IncidentState
    timestamp: datetime
    reason: str


class Trigger(Model):
    source: str
    fingerprint: str
    observed_at: datetime
    raw: str
    normalized: dict[str, Any]


class IncidentDetail(Incident):
    steps: list[Step]
    transitions: list[Transition]
    events: list[Trigger]


class ScannerStatus(Model):
    name: str
    type: str
    target: str
    state: str = "stopped"
    last_event: datetime | None = None
    reconnect_count: int = 0
    last_error: str | None = None
