from fastapi import APIRouter

from yubarta.entrypoints.api_server.v1.routes.control import router as control_router

router = APIRouter(prefix="/api/v1")
router.include_router(control_router)
