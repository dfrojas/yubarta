import hashlib
from http import HTTPStatus
from datetime import datetime, timezone
import json
from dataclasses import asdict


from fastapi import APIRouter, Request, Response, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from yubarta.core.models import Alert
from yubarta.core.enums import AlertSource

from yubarta.drivers.monitoring.datadog import DatadogHandler
from yubarta.entrypoints.api_server.v1.schemas import AlertReceiptResponse
from yubarta.core.enums import AlertStatus
from yubarta.core.interfaces import AlarmStorageInterface
from yubarta.drivers.db.repository import SqlAlchemyAlarmRepository
from yubarta.drivers.db.utils import get_session
from yubarta.drivers.messaging.kafka import producer
from yubarta.config import settings

from yubarta.controllers.alarms import AlertController
from yubarta.common.utils import generate_fingerprint
router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("/register/datadog", response_model=AlertReceiptResponse, status_code=HTTPStatus.ACCEPTED)
async def receive_alert(request: Request, db: Session = Depends(get_session)):
    try:
        payload = await request.json()

        now = datetime.now(timezone.utc).isoformat()
        fingerprint = generate_fingerprint(AlertSource.DATADOG, now)
        alert = DatadogHandler(payload, fingerprint, now).process()

        await AlertController(messaging=producer).process_alert(alert)

        return AlertReceiptResponse(
            alert_id=alert.fingerprint,
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
