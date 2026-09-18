"""Liveness probe. Kept unversioned and unauthenticated for orchestrators."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from yubarta.api.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(ok=True, time=datetime.now(timezone.utc))
