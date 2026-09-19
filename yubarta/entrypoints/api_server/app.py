"""FastAPI application factory for the Control API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from yubarta.config.settings import AppConfig
from yubarta.entrypoints.api_server.health import router as health_router
from yubarta.entrypoints.api_server.security import resolve_api_token
from yubarta.entrypoints.api_server.v1.router import api_v1_router
from yubarta.runtime import YubartaRuntime


@asynccontextmanager
async def _noop_lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield


@asynccontextmanager
async def _runtime_lifespan(app: FastAPI) -> AsyncIterator[None]:
    runtime: YubartaRuntime = app.state.runtime
    async with runtime.lifespan():
        yield


def create_app(runtime: YubartaRuntime, *, manage_runtime: bool = False) -> FastAPI:
    """Build the app around a runtime.

    ``manage_runtime=True`` lets the lifespan own setup/start/shutdown. Tests
    pass a runtime they already manage and leave it ``False``.
    """
    app = FastAPI(
        title="Yubarta Control API",
        version="1.0.0",
        lifespan=_runtime_lifespan if manage_runtime else _noop_lifespan,
    )
    app.state.runtime = runtime
    app.state.api_token = resolve_api_token(runtime.config)
    app.include_router(health_router)
    app.include_router(api_v1_router)
    return app


def create_app_from_config(config: AppConfig, apply: bool, database_url: str = "") -> tuple[FastAPI, YubartaRuntime]:
    runtime = YubartaRuntime(config, apply=apply, database_url=database_url)
    return create_app(runtime, manage_runtime=True), runtime
