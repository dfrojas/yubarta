from http import HTTPStatus
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from yubarta.controllers.alarms import AlertController
from yubarta.drivers.messaging.kafka import producer
from yubarta.entrypoints.api_server.schemas import AlertRequest, AlertResponse

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("/register/datadog", response_model=AlertResponse, status_code=HTTPStatus.ACCEPTED)
async def receive_alert(alert: AlertRequest) -> AlertResponse | JSONResponse:
    try:
        # now = datetime.now(timezone.utc).isoformat()
        # fingerprint = generate_fingerprint(AlertSource.DATADOG, now)
        # alert_converted = AlertKafkaMessage(
        #     id=fingerprint,
        #     source=AlertSource.DATADOG,
        #     severity=payload["alert_type"],
        #     labels=payload["tags"],
        #     status=AlertStatus.PENDING,
        # )

        received_at = datetime.utcnow()
        alert_domain = await AlertController(messaging=producer).process_alert(alert, received_at=received_at)

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
