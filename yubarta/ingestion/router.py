from fastapi import APIRouter

from .routes import z
from .routes.webhook import router as webhook_router

router = APIRouter(prefix="/api/v1")

router.include_router(z.router)
router.include_router(webhook_router, prefix="/webhook")
