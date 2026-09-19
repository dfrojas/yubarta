"""Integration: FastAPI routes + CLI as HTTP client over real HTTP."""

from __future__ import annotations

import httpx


async def test_healthz(server_url: str) -> None:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{server_url}/healthz")
    assert response.status_code == 200
    assert response.json()["ok"] is True


async def test_status_scanners_incidents(server_url: str) -> None:
    async with httpx.AsyncClient() as client:
        status = (await client.get(f"{server_url}/api/v1/status")).json()
        assert status["mode"] == "dry-run"
        assert (await client.get(f"{server_url}/api/v1/scanners")).status_code == 200
        assert (await client.get(f"{server_url}/api/v1/incidents")).status_code == 200
        assert (await client.get(f"{server_url}/api/v1/incidents/missing")).status_code == 404


def test_cli_uses_http_not_postgres(server_url: str) -> None:
    from typer.testing import CliRunner

    from yubarta.cli import app as cli_app

    runner = CliRunner()
    result = runner.invoke(cli_app, ["health", "--server", server_url])
    assert result.exit_code == 0, result.output
    assert "ok" in result.output
    result = runner.invoke(cli_app, ["status", "--server", server_url])
    assert result.exit_code == 0, result.output
    assert "dry-run" in result.output
