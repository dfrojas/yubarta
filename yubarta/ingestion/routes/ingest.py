from http import HTTPStatus

from fastapi import APIRouter
from fastapi.responses import JSONResponse

# from yubarta.infra.messaging.kafka import producer
# from yubarta.infra.cache.redis import idempotency_check, bump_batch_alarms
# from yubarta.domain.signal import Signal

router = APIRouter(prefix="/ingest", tags=["ingest"])

# TODO(signal-ingestion): implement generic Alertmanager webhook normalization → Signal
# Reference flow (to be restored in signal-ingestion change):
#
# BATCH_THRESHOLD = 3
#
# @router.post("/webhook", status_code=HTTPStatus.ACCEPTED)
# async def receive_alert(payload: dict) -> JSONResponse:
#     signal = Signal.from_webhook(payload)
#
#     is_new = await idempotency_check(event_id=signal.id)
#     if not is_new:
#         return JSONResponse(
#             status_code=HTTPStatus.ACCEPTED,
#             content={"message": "duplicate_event_ignored", "event_id": signal.id}
#         )
#
#     batch_count = await bump_batch_alarms(signal.fingerprint, window_sec=60)
#     eligible = batch_count >= BATCH_THRESHOLD
#
#     if eligible:
#         await producer.publish(topic="yubarta.signals", signal=signal)
#
#     return JSONResponse(
#         status_code=HTTPStatus.ACCEPTED,
#         content={
#             "message": "signal received",
#             "signal_id": signal.id,
#             "batch_count": batch_count,
#             "eligible_for_director": eligible,
#         },
#     )

@router.post("/confluent", status_code=HTTPStatus.ACCEPTED)
async def receive_confluent_alert() -> JSONResponse:
    return JSONResponse(
        status_code=HTTPStatus.ACCEPTED,
        content={"message": "stub — pending signal-ingestion change"},
    )
