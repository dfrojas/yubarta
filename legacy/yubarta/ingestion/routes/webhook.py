import logging
from http import HTTPStatus
from typing import Annotated, Any

from fastapi import APIRouter, Depends

from yubarta.domain.ports import IncidentStore
from yubarta.incident.dependencies import get_incident_store
from yubarta.ingestion.normalizers.alertmanager import normalize_alertmanager
from yubarta.ingestion.schemas import (
    AcceptedAlert,
    IngestionResult,
    RejectedAlert,
    RejectionReason,
)
from yubarta.inventory.dependencies import get_inventory
from yubarta.inventory.matcher import AmbiguousTargetError, NoMatchingTargetError, match_target_entry
from yubarta.inventory.schema import Inventory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alertmanager", tags=["webhook"])


@router.post("", status_code=HTTPStatus.ACCEPTED)
async def receive_alertmanager(
    payload: dict[str, Any],
    store: Annotated[IncidentStore, Depends(get_incident_store)],
    inventory: Annotated[Inventory, Depends(get_inventory)],
) -> IngestionResult:
    """Normalize an Alertmanager delivery, resolve each alert to a target, and open
    an incident for the ones that resolve.

    Always 202 for a well-formed payload, including when every alert is rejected. A
    rejected alert is a request the system cannot act on, not a malformed one, and a
    non-2xx would make Alertmanager retry the whole batch on a schedule that no
    retry can fix, re-delivering the alerts that did succeed along with it.

    This is intake and it stops here. Nothing decides what to do about the incident
    until the Director exists.
    """
    accepted: list[AcceptedAlert] = []
    rejected: list[RejectedAlert] = []

    for signal in normalize_alertmanager(payload):
        try:
            target_name, _ = match_target_entry(inventory, signal)
        except NoMatchingTargetError as error:
            logger.warning("signal %s matched no target: %s", signal.id, error)
            rejected.append(
                RejectedAlert(
                    signal_id=signal.id,
                    reason=RejectionReason.no_matching_target,
                    detail=str(error),
                )
            )
            continue
        except AmbiguousTargetError as error:
            logger.warning("signal %s matched several targets: %s", signal.id, error)
            rejected.append(
                RejectedAlert(
                    signal_id=signal.id,
                    reason=RejectionReason.ambiguous_target,
                    detail=str(error),
                )
            )
            continue

        incident = await store.create(signal, target_name)
        logger.info("signal %s opened incident %s on %s", signal.id, incident.id, target_name)
        accepted.append(
            AcceptedAlert(
                signal_id=signal.id,
                incident_id=incident.id,
                target_name=incident.target_name,
                state=incident.state,
            )
        )

    return IngestionResult(accepted=accepted, rejected=rejected)
