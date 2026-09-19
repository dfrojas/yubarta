"""Versioned router aggregation. Auth is applied once at the router level."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from yubarta.entrypoints.api_server.security import require_bearer
from yubarta.entrypoints.api_server.v1.routes import incidents, scanners, status

api_v1_router = APIRouter(
    prefix="/api/v1",
    dependencies=[Depends(require_bearer)],
)

api_v1_router.include_router(status.router)
api_v1_router.include_router(scanners.router)
api_v1_router.include_router(incidents.router)
