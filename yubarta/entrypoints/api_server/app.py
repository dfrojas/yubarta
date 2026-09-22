from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from yubarta.entrypoints.api_server.health import router as health_router
from yubarta.entrypoints.api_server.v1.router import router
from yubarta.entrypoints.api_server.v1.routes.control import router as control_router
from yubarta.runtime import YubartaRuntime


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    if app.state.manage_runtime:
        async with app.state.runtime.lifespan():
            yield
    else:
        yield


def create_app(runtime: YubartaRuntime, manage_runtime: bool = True) -> FastAPI:
    app = FastAPI(title="Yubarta", version="1.0.0", lifespan=lifespan)
    app.state.runtime = runtime
    app.state.manage_runtime = manage_runtime
    app.include_router(health_router)
    app.include_router(router)
    app.include_router(control_router, include_in_schema=False)
    return app
