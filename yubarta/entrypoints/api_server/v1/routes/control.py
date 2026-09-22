from time import monotonic
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from yubarta.core.models import Incident, IncidentDetail, ScannerStatus
from yubarta.entrypoints.api_server.dependencies import RuntimeDep
from yubarta.entrypoints.api_server.schemas import StatusResponse
from yubarta.entrypoints.api_server.security import require_bearer

router = APIRouter(tags=["control"], dependencies=[Depends(require_bearer)])


@router.get("/status")
async def status(runtime: RuntimeDep) -> StatusResponse:
    healthy = await runtime.database_healthy()
    if not healthy:
        raise HTTPException(503, "Database unavailable")
    recent = await runtime.incidents.list(1)
    return StatusResponse(uptime=monotonic() - runtime.started_at, database_healthy=healthy,
                          mode="apply" if runtime.apply else "dry-run", target=runtime.config.target.host,
                          scanners=runtime.supervisor.statuses(), active_incident_count=await runtime.incidents.active_count(),
                          most_recent_incident=recent[0] if recent else None)


@router.get("/scanners")
async def scanners(runtime: RuntimeDep) -> list[ScannerStatus]:
    return runtime.supervisor.statuses()


@router.get("/incidents")
async def incidents(runtime: RuntimeDep, limit: Annotated[int, Query(ge=1, le=1000)] = 100) -> list[Incident]:
    return await runtime.incidents.list(limit)


@router.get("/incidents/{incident_id}")
async def incident(incident_id: UUID, runtime: RuntimeDep) -> IncidentDetail:
    detail = await runtime.incidents.detail(incident_id)
    if detail is None:
        raise HTTPException(404, "Incident not found")
    return detail
