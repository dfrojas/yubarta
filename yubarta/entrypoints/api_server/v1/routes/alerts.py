from datetime import datetime, timezone
from http import HTTPStatus

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from yubarta.common.utils import generate_fingerprint
from yubarta.controllers.alarms import AlertController
from yubarta.core.enums import AlertSource, AlertStatus
from yubarta.drivers.messaging.kafka import producer
from yubarta.drivers.monitoring.datadog import DatadogHandler
from yubarta.entrypoints.api_server.v1.schemas import AlertReceiptResponse

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("/register/datadog", response_model=AlertReceiptResponse, status_code=HTTPStatus.ACCEPTED)
async def receive_alert(request: Request):
    try:
        payload = await request.json()

        now = datetime.now(timezone.utc).isoformat()
        fingerprint = generate_fingerprint(AlertSource.DATADOG, now)

        alert_converted = DatadogHandler(payload, fingerprint, now).process()

        await AlertController(messaging=producer).process_alert(alert_converted)

        return AlertReceiptResponse(
            alert_id=alert_converted.fingerprint,
            status=AlertStatus.PENDING,
        )

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
