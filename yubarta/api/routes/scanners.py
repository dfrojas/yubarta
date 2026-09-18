"""Scanner status endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from yubarta.api.dependencies import RuntimeDep
from yubarta.api.schemas import ScannerInfo

router = APIRouter(tags=["scanners"])


@router.get("/scanners", response_model=list[ScannerInfo])
async def list_scanners(runtime: RuntimeDep) -> list[ScannerInfo]:
    return [ScannerInfo.model_validate(status_item) for status_item in runtime.supervisor.statuses()]
