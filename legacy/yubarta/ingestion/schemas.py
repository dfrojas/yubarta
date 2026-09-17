from enum import StrEnum

from pydantic import BaseModel

from yubarta.incident.models import IncidentState


class RejectionReason(StrEnum):
    no_matching_target = "no_matching_target"
    ambiguous_target = "ambiguous_target"


class AcceptedAlert(BaseModel):
    signal_id: str
    incident_id: str
    target_name: str
    state: IncidentState


class RejectedAlert(BaseModel):
    signal_id: str
    reason: RejectionReason
    detail: str


class IngestionResult(BaseModel):
    """Per-alert outcome of one webhook delivery.

    Reported per alert rather than per request because a delivery can be partly
    actionable: one alert resolving to no target says nothing about the others in
    the same payload.
    """

    accepted: list[AcceptedAlert]
    rejected: list[RejectedAlert]
