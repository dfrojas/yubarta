from datetime import datetime, timezone
from http import HTTPStatus

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from yubarta.controllers.alarms import AlertController
from yubarta.drivers.messaging.kafka import producer
from yubarta.entrypoints.api_server.schemas import AlertRequest, AlertResponse

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("/register/datadog", response_model=AlertResponse, status_code=HTTPStatus.ACCEPTED)
async def receive_alert(alert_request: AlertRequest) -> AlertResponse | JSONResponse:
    try:
        now = datetime.now(timezone.utc)
        alert = alert_request.to_domain(now)
        alert_domain = await AlertController(messaging=producer).process_alert(alert)

        return AlertResponse(alert_id=alert_domain.fingerprint, status=str(alert_domain.status))

    except ValueError as e:
        return JSONResponse(
            status_code=HTTPStatus.BAD_REQUEST,
            content={"error": str(e)},
        )
    except Exception as e:
        return JSONResponse(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            content={"error": f"Unexpected error: {str(e)}"},
        )
