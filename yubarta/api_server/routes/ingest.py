from datetime import datetime, timezone
from http import HTTPStatus

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from yubarta.drivers.messaging.kafka import producer
from yubarta.models.alerts import Alert
from yubarta.drivers.cache.redis import idempotency_check, bump_batch_alarms

router = APIRouter(prefix="/ingest", tags=["ingest"])


BATCH_THRESHOLD = 3

@router.post("/confluent", status_code=HTTPStatus.ACCEPTED)
async def receive_confluent_alert():
    normalized_mocked = {
            "id": "alert-0001",
            "source": "confluent",
            "type": "consumer_lag",
            "severity": "critical",
            "service": "ingester",
            "group_id": "consumer_group_42",
            "topic": "event_stream",
            "lag": 50950,
            "window": "10m",
            "threshold": 20000,
            "fired_at": "2025-08-26T19:10:10Z",
            "labels": {
                "env": "prod",
                "team": "data-platform",
                "region": "eu-central"
            },
        }

    alert = Alert(**normalized_mocked)

    # TODO: Publicar en Indexer topic

    # is_new = await idempotency_check(event_id=alert.event_id)
    # if not is_new:
    #     return JSONResponse(
    #         status_code=HTTPStatus.ACCEPTED,
    #         content={"message": "duplicate_event_ignored", "event_id": alert.event_id}
    #     )

    batch_count = await bump_batch_alarms(alert.fingerprint, window_sec=60)

    eligible = (batch_count >= BATCH_THRESHOLD)

    if eligible:
        await producer.publish(
            topic="yubarta.alerts", value=alert.model_dump(), key=alert.event_id
        )

    return JSONResponse(
        status_code=HTTPStatus.ACCEPTED,
        content={
            "message": "Alert received",
            "event_id": alert.event_id,
            "batch_count": batch_count,
            "eligible_for_director": eligible
        }
    )
