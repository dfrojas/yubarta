"""Typer CLI. Always an HTTP client of the Control API, never reads Postgres."""

from __future__ import annotations

import json
import os

import httpx
import typer

app = typer.Typer(help="Yubarta control CLI (HTTP client of the Control API)")

API_PREFIX = "/api/v1"


def _server_url(server: str | None) -> str:
    return (server or os.environ.get("YUBARTA_SERVER_URL", "http://127.0.0.1:8787")).rstrip("/")


def _auth_headers() -> dict[str, str]:
    token = os.environ.get("YUBARTA_API_TOKEN", "")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def _get(server: str | None, path: str) -> object:
    url = _server_url(server) + path
    try:
        response = httpx.get(url, headers=_auth_headers(), timeout=15.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        typer.echo(f"Request failed: {exc}", err=True)
        raise typer.Exit(1)
    return response.json()


@app.command()
def health(server: str | None = typer.Option(None, "--server", help="Control API base URL")) -> None:
    typer.echo(json.dumps(_get(server, "/health"), indent=2))


@app.command()
def status(server: str | None = typer.Option(None, "--server", help="Control API base URL")) -> None:
    typer.echo(json.dumps(_get(server, f"{API_PREFIX}/status"), indent=2))


@app.command()
def scanners(server: str | None = typer.Option(None, "--server", help="Control API base URL")) -> None:
    typer.echo(json.dumps(_get(server, f"{API_PREFIX}/scanners"), indent=2))


@app.command()
def incidents(server: str | None = typer.Option(None, "--server", help="Control API base URL")) -> None:
    typer.echo(json.dumps(_get(server, f"{API_PREFIX}/incidents"), indent=2))


@app.command()
def incident(
    incident_id: str = typer.Argument(..., help="Incident id"),
    server: str | None = typer.Option(None, "--server", help="Control API base URL"),
) -> None:
    typer.echo(json.dumps(_get(server, f"{API_PREFIX}/incidents/{incident_id}"), indent=2))


if __name__ == "__main__":
    app()
