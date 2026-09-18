"""Incident lifecycle state machine with one centralized transition mechanism."""

from __future__ import annotations

import enum

from yubarta.incidents.errors import InvalidTransitionError


class IncidentState(str, enum.Enum):
    DETECTED = "DETECTED"
    DIAGNOSING = "DIAGNOSING"
    PRECHECKING = "PRECHECKING"
    REMEDIATING = "REMEDIATING"
    VERIFYING = "VERIFYING"
    RESOLVED = "RESOLVED"
    FAILED = "FAILED"


_ALLOWED: dict[IncidentState, set[IncidentState]] = {
    IncidentState.DETECTED: {IncidentState.DIAGNOSING},
    IncidentState.DIAGNOSING: {IncidentState.PRECHECKING},
    IncidentState.PRECHECKING: {IncidentState.REMEDIATING, IncidentState.RESOLVED, IncidentState.FAILED},
    IncidentState.REMEDIATING: {IncidentState.VERIFYING, IncidentState.FAILED},
    IncidentState.VERIFYING: {IncidentState.RESOLVED, IncidentState.REMEDIATING, IncidentState.FAILED},
    IncidentState.RESOLVED: set(),
    IncidentState.FAILED: set(),
}


def allowed_transitions(state: IncidentState) -> set[IncidentState]:
    return set(_ALLOWED[state])


def transition(state: IncidentState, target: IncidentState) -> IncidentState:
    """Centralized transition mechanism. Raises InvalidTransitionError when illegal."""
    if target not in _ALLOWED[state]:
        raise InvalidTransitionError(f"Invalid transition {state.value} -> {target.value}")
    return target
