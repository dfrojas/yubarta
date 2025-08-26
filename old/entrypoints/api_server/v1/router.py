from fastapi import APIRouter

from .routes import alerts, health

router = APIRouter(prefix="/api/v1")

router.include_router(alerts.router)
router.include_router(health.router)
