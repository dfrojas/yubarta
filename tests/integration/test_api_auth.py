"""Integration: bearer-token auth on the versioned Control API."""

from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI

from yubarta.api import create_app
from yubarta.config import ApiConfig, AppConfig, TargetConfig
from yubarta.runtime import YubartaRuntime

TOKEN = "s3cret-token"
ENV_NAME = "YUBARTA_TEST_API_TOKEN"


@pytest.fixture()
async def auth_app(monkeypatch, tmp_path):  # type: ignore[no-untyped-def]
    monkeypatch.setenv(ENV_NAME, TOKEN)
    config = AppConfig(
        target=TargetConfig(host="vm", user="u", key=""),
        api=ApiConfig(token_from_env=ENV_NAME),
    )
    runtime = YubartaRuntime(config, apply=False, database_url=f"sqlite+aiosqlite:///{tmp_path}/auth.db")
    await runtime.setup()
    yield create_app(runtime)
    await runtime.shutdown()


async def _get(app: FastAPI, path: str, headers: dict[str, str] | None = None) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path, headers=headers or {})


async def test_health_is_open(auth_app):  # type: ignore[no-untyped-def]
    assert (await _get(auth_app, "/health")).status_code == 200


async def test_versioned_route_requires_token(auth_app):  # type: ignore[no-untyped-def]
    response = await _get(auth_app, "/api/v1/status")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


async def test_versioned_route_rejects_wrong_token(auth_app):  # type: ignore[no-untyped-def]
    response = await _get(auth_app, "/api/v1/status", {"Authorization": "Bearer wrong"})
    assert response.status_code == 401


async def test_versioned_route_accepts_token(auth_app):  # type: ignore[no-untyped-def]
    response = await _get(auth_app, "/api/v1/status", {"Authorization": f"Bearer {TOKEN}"})
    assert response.status_code == 200


def test_missing_token_env_fails_fast(monkeypatch):  # type: ignore[no-untyped-def]
    monkeypatch.delenv(ENV_NAME, raising=False)
    config = AppConfig(
        target=TargetConfig(host="vm", user="u", key=""),
        api=ApiConfig(token_from_env=ENV_NAME),
    )
    runtime = YubartaRuntime(config, apply=False, database_url="sqlite+aiosqlite:///:memory:")
    with pytest.raises(RuntimeError):
        create_app(runtime)
