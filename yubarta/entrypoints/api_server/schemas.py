"""Pydantic response models for the Control API.

These are the public wire contracts. They are intentionally separate from the
persistence rows and the domain models, so storage changes never leak to the API.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


class HealthResponse(BaseModel):
    ok: bool
    time: datetime


class StatusResponse(BaseModel):
    uptime_seconds: float
    database_ok: bool
    mode: Literal["apply", "dry-run"]
    target: str
    active_incidents: int
    most_recent_incident_id: str | None


class ScannerInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    kind: str
    target: str
    connected: bool
    running: bool
    last_event_at: str | None
    reconnect_count: int
    last_error: str | None

    @field_validator("last_event_at", mode="before")
    @classmethod
    def serialize_observation_time(cls, value: datetime | str | None) -> str | None:
        return value.isoformat() if isinstance(value, datetime) else value


class IncidentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    target: str
    incident_type: str
    state: str
    version: int
    opened_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    resolved_by_step_id: str | None
    failure_reason: str | None


class StepInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sequence: int
    kind: str
    name: str
    state: str
    exit_code: int | None
    stdout_excerpt: str | None
    stderr_excerpt: str | None
    error: str | None


class TransitionInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    from_state: str
    to_state: str
    created_at: datetime
    reason: str


class IncidentDetail(IncidentSummary):
    steps: list[StepInfo]
    transitions: list[TransitionInfo]
