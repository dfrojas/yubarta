from typing import Literal

from yubarta.core.models import Incident, Model, ScannerStatus


class HealthResponse(Model):
    status: Literal["ok", "unavailable"]


class StatusResponse(Model):
    uptime: float
    database_healthy: bool
    mode: Literal["dry-run", "apply"]
    target: str
    scanners: list[ScannerStatus]
    active_incident_count: int
    most_recent_incident: Incident | None
