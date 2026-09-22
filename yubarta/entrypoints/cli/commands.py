import json
import os
from typing import Annotated
from uuid import UUID

import httpx
import typer

app = typer.Typer(no_args_is_help=True)


@app.callback()
def configure(context: typer.Context,
              server: Annotated[str, typer.Option(envvar="YUBARTA_SERVER_URL")] = "http://127.0.0.1:8787") -> None:
    context.obj = server.rstrip("/")


def request(context: typer.Context, path: str) -> None:
    token = os.environ.get("YUBARTA_API_TOKEN")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        response = httpx.get(f"{context.obj}{path}", headers=headers, timeout=10)
        response.raise_for_status()
        typer.echo(json.dumps(response.json(), indent=2))
    except (httpx.HTTPError, ValueError) as error:
        typer.echo(f"API request failed: {error}", err=True)
        raise typer.Exit(1) from error


@app.command()
def health(context: typer.Context) -> None:
    request(context, "/health")


@app.command()
def status(context: typer.Context) -> None:
    request(context, "/api/v1/status")


@app.command()
def scanners(context: typer.Context) -> None:
    request(context, "/api/v1/scanners")


@app.command()
def incidents(context: typer.Context) -> None:
    request(context, "/api/v1/incidents")


@app.command()
def incident(context: typer.Context, incident_id: UUID) -> None:
    request(context, f"/api/v1/incidents/{incident_id}")
