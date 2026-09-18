"""Liveness probe and health endpoints. Kept unversioned and unauthenticated for orchestrators."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Response

from yubarta.api.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/whale")
def whale() -> Response:
    whale_ascii = r"""
         .
        ":"
      ___:____     |"\/"|
    ,'        `.    \  /
    |  O        \___/  |
~^~^~^~^~^~^~^~^~^~^~^~^~
"""
    return Response(content=whale_ascii, media_type="text/plain")


@router.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    return HealthResponse(ok=True, time=datetime.now(timezone.utc))
