from yubarta.core.enums import IncidentState
from yubarta.core.errors import InvalidTransitionError


def validate_transition(current: IncidentState, destination: IncidentState) -> None:
    allowed = {
        IncidentState.DETECTED: {IncidentState.DIAGNOSING, IncidentState.FAILED},
        IncidentState.DIAGNOSING: {IncidentState.PRECHECKING, IncidentState.FAILED},
        IncidentState.PRECHECKING: {IncidentState.REMEDIATING, IncidentState.RESOLVED, IncidentState.FAILED},
        IncidentState.REMEDIATING: {IncidentState.VERIFYING, IncidentState.FAILED},
        IncidentState.VERIFYING: {IncidentState.REMEDIATING, IncidentState.RESOLVED, IncidentState.FAILED},
        IncidentState.RESOLVED: set(),
        IncidentState.FAILED: set(),
    }
    if destination not in allowed[current]:
        raise InvalidTransitionError(f"Invalid incident transition: {current} -> {destination}")
