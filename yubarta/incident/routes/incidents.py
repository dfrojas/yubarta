from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from yubarta.domain.ports import IncidentStore
from yubarta.incident.dependencies import get_incident_store
from yubarta.incident.models import Incident
from yubarta.incident.schemas import IncidentDetail

router = APIRouter(prefix="/incidents", tags=["incidents"])

DEFAULT_LIST_LIMIT = 20
MAX_LIST_LIMIT = 100


@router.get("/{incident_id}")
async def read_incident(
    incident_id: str,
    store: Annotated[IncidentStore, Depends(get_incident_store)],
) -> IncidentDetail:
    incident = await store.get(incident_id)
    if incident is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"incident '{incident_id}' does not exist",
        )
    transitions = await store.list_transitions(incident_id)
    return IncidentDetail(incident=incident, transitions=transitions)


@router.get("")
async def list_incidents(
    store: Annotated[IncidentStore, Depends(get_incident_store)],
    target_name: str | None = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIST_LIMIT)] = DEFAULT_LIST_LIMIT,
) -> list[Incident]:
    """Most recent incidents first, always bounded.

    An unbounded default would be a read that gets slower every day the system
    runs, and no caller of this route wants the whole table.
    """
    if target_name is not None:
        return (await store.list_by_target(target_name))[:limit]
    return await store.list_recent(limit)
