"""Incident list and detail endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, status

from yubarta.entrypoints.api_server.dependencies import IncidentServiceDep
from yubarta.entrypoints.api_server.schemas import IncidentDetail, IncidentSummary, StepInfo, TransitionInfo

router = APIRouter(tags=["incidents"])


@router.get("/incidents", response_model=list[IncidentSummary])
async def list_incidents(service: IncidentServiceDep) -> list[IncidentSummary]:
    rows = await service.list_incidents()
    return [IncidentSummary.model_validate(row) for row in rows]


@router.get("/incidents/{incident_id}", response_model=IncidentDetail)
async def get_incident(
    incident_id: Annotated[str, Path(description="Incident id")],
    service: IncidentServiceDep,
) -> IncidentDetail:
    detail = await service.get_incident(incident_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    summary = IncidentSummary.model_validate(detail.incident)
    return IncidentDetail(
        **summary.model_dump(),
        steps=[StepInfo.model_validate(step) for step in detail.steps],
        transitions=[TransitionInfo.model_validate(item) for item in detail.transitions],
    )
