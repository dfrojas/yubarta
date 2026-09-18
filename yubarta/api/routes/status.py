"""Runtime status endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from yubarta.api.dependencies import IncidentRepositoryDep, RuntimeDep
from yubarta.api.schemas import StatusResponse

router = APIRouter(tags=["status"])


@router.get("/status", response_model=StatusResponse)
async def get_status(runtime: RuntimeDep, repository: IncidentRepositoryDep) -> StatusResponse:
    active = 0
    most_recent: str | None = None
    if repository is not None:
        incidents = await repository.list_incidents(limit=50)
        active = sum(1 for item in incidents if item.state not in ("RESOLVED", "FAILED"))
        most_recent = incidents[0].id if incidents else None
    return StatusResponse(
        uptime_seconds=runtime.uptime_seconds,
        database_ok=runtime.db_healthy,
        mode="apply" if runtime.apply else "dry-run",
        target=runtime.config.target.host,
        active_incidents=active,
        most_recent_incident_id=most_recent,
    )
