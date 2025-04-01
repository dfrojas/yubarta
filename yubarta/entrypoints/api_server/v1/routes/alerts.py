from http import HTTPStatus

from fastapi import APIRouter, Request, Response, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from yubarta.core.models import Alert

from yubarta.drivers.monitoring.datadog import DatadogHandler
from yubarta.entrypoints.api_server.v1.schemas import AlertReceiptResponse
import asyncio
from yubarta.core.enums import AlertStatus
from yubarta.core.interfaces import AlarmStorageInterface
from yubarta.drivers.db.repository import SqlAlchemyAlarmRepository
from yubarta.drivers.db.utils import get_session


alert_queue = asyncio.Queue()  # In-memory queue for now (will be replaced by Kafka later)
router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertService:
    def __init__(self, repository: AlarmStorageInterface):
        self.repository = repository

    async def process_alert(self, alert: Alert):
        await self.repository.add(alert)


@router.post("/register/datadog", response_model=AlertReceiptResponse)
async def receive_alert(request: Request, db: Session = Depends(get_session)):
    try:
        payload = await request.json()

        alert = DatadogHandler(payload).process()

        await alert_queue.put(alert)
        await AlertService(SqlAlchemyAlarmRepository(db)).process_alert(alert)

        return AlertReceiptResponse(
            alert_id=alert.id,
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
