from fastapi import APIRouter, Response

from yubarta.entrypoints.api_server.dependencies import RuntimeDep
from yubarta.entrypoints.api_server.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health")
@router.get("/healthz", include_in_schema=False)
async def health(runtime: RuntimeDep, response: Response) -> HealthResponse:
    healthy = runtime.running and await runtime.database_healthy()
    response.status_code = 200 if healthy else 503
    return HealthResponse(status="ok" if healthy else "unavailable")
