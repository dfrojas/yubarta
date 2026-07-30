from fastapi import APIRouter

from .routes.incidents import router as incidents_router

router = APIRouter(prefix="/api/v1")

router.include_router(incidents_router)
