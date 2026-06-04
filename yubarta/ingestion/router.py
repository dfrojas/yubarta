from fastapi import APIRouter

from .routes import ingest, z

router = APIRouter(prefix="/api/v1")

router.include_router(ingest.router)
router.include_router(z.router)
