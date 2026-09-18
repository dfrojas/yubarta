"""Incident list and detail endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, status

from yubarta.api.dependencies import IncidentRepositoryDep
from yubarta.api.schemas import IncidentDetail, IncidentSummary, StepInfo, TransitionInfo

router = APIRouter(tags=["incidents"])


@router.get("/incidents", response_model=list[IncidentSummary])
async def list_incidents(repository: IncidentRepositoryDep) -> list[IncidentSummary]:
    rows = await repository.list_incidents()
    return [IncidentSummary.model_validate(row) for row in rows]


@router.get("/incidents/{incident_id}", response_model=IncidentDetail)
async def get_incident(
    incident_id: Annotated[str, Path(description="Incident id")],
    repository: IncidentRepositoryDep,
) -> IncidentDetail:
    row = await repository.get(incident_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    steps = await repository.list_steps(incident_id)
    transitions = await repository.list_transitions(incident_id)
    summary = IncidentSummary.model_validate(row)
    return IncidentDetail(
        **summary.model_dump(),
        steps=[StepInfo.model_validate(step) for step in steps],
        transitions=[TransitionInfo.model_validate(item) for item in transitions],
    )
