from http import HTTPStatus

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from yubarta.domain.ports import SignalStore
from yubarta.ingestion.dependencies import get_signal_store
from yubarta.ingestion.normalizers.alertmanager import normalize_alertmanager

router = APIRouter(prefix="/alertmanager", tags=["webhook"])


@router.post("", status_code=HTTPStatus.ACCEPTED)
async def receive_alertmanager(
    payload: dict,
    store: SignalStore = Depends(get_signal_store),
) -> JSONResponse:
    signals = normalize_alertmanager(payload)
    signal_ids = []
    for signal in signals:
        stored = await store.add(signal)
        signal_ids.append(stored.id)
    return JSONResponse(
        status_code=HTTPStatus.ACCEPTED,
        content={"signal_ids": signal_ids},
    )
