"""Control API fixtures: in-process app and live HTTP server."""

from __future__ import annotations

import threading
import time
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
import uvicorn
from fastapi import FastAPI
from sqlalchemy.pool import NullPool

from tests.fixtures.ports import free_port
from yubarta.config.settings import ApiConfig, AppConfig, TargetConfig
from yubarta.entrypoints.api_server import create_app
from yubarta.runtime import YubartaRuntime

TOKEN = "s3cret-token"
ENV_NAME = "YUBARTA_TEST_API_TOKEN"


@pytest.fixture()
async def auth_app(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> AsyncIterator[FastAPI]:
    monkeypatch.setenv(ENV_NAME, TOKEN)
    config = AppConfig(
        target=TargetConfig(host="vm", user="u", key=""),
        api=ApiConfig(token_from_env=ENV_NAME),
    )
    runtime = YubartaRuntime(config, apply=False, database_url=f"sqlite+aiosqlite:///{tmp_path}/auth.db")
    await runtime.setup()
    yield create_app(runtime)
    await runtime.shutdown()


@pytest.fixture()
async def server_url(test_db: str) -> AsyncIterator[str]:
    config = AppConfig(target=TargetConfig(host="vm", user="u", key=""))
    runtime = YubartaRuntime(
        config,
        apply=False,
        database_url=test_db,
        engine_options={"poolclass": NullPool},
    )
    await runtime.setup()
    app = create_app(runtime)
    port = free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            response = httpx.get(f"{base}/healthz", timeout=2.0)
            if response.status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.1)
    yield base
    await runtime.shutdown()
    server.should_exit = True
    thread.join(timeout=15.0)
