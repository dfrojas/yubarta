"""Integration: FastAPI routes + CLI as HTTP client over real HTTP."""

from __future__ import annotations

import socket
import threading
import time

import httpx
import pytest
import uvicorn
from sqlalchemy.pool import NullPool

from yubarta.api import create_app
from yubarta.config import AppConfig, TargetConfig
from yubarta.runtime import YubartaRuntime


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture()
async def server_url(test_db):  # type: ignore[no-untyped-def]
    config = AppConfig(target=TargetConfig(host="vm", user="u", key=""))
    runtime = YubartaRuntime(
        config, apply=False, database_url=test_db, engine_options={"poolclass": NullPool}
    )
    await runtime.setup()
    app = create_app(runtime)
    port = _free_port()
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


async def test_healthz(server_url):  # type: ignore[no-untyped-def]
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{server_url}/healthz")
    assert response.status_code == 200
    assert response.json()["ok"] is True


async def test_status_scanners_incidents(server_url):  # type: ignore[no-untyped-def]
    async with httpx.AsyncClient() as client:
        status = (await client.get(f"{server_url}/api/v1/status")).json()
        assert status["mode"] == "dry-run"
        assert (await client.get(f"{server_url}/api/v1/scanners")).status_code == 200
        assert (await client.get(f"{server_url}/api/v1/incidents")).status_code == 200
        assert (await client.get(f"{server_url}/api/v1/incidents/missing")).status_code == 404


def test_cli_uses_http_not_postgres(server_url):  # type: ignore[no-untyped-def]
    from typer.testing import CliRunner

    from yubarta.cli import app as cli_app

    runner = CliRunner()
    result = runner.invoke(cli_app, ["health", "--server", server_url])
    assert result.exit_code == 0, result.output
    assert "ok" in result.output
    result = runner.invoke(cli_app, ["status", "--server", server_url])
    assert result.exit_code == 0, result.output
    assert "dry-run" in result.output
