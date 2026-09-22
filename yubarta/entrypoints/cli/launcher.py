"""Single executable: `yubarta`. `serve` starts DB + runtime + scanners + FastAPI."""

from __future__ import annotations

import typer
import uvicorn

from yubarta.drivers.config.loader import load_config
from yubarta.entrypoints.api_server import create_app_from_config
from yubarta.entrypoints.cli import commands

app = typer.Typer(help="Yubarta autonomous remediation agent")


@app.command()
def serve(
    config: str = typer.Option("/etc/yubarta/config.yaml", "--config", help="Config file path"),
    apply: bool = typer.Option(False, "--apply", help="Enable real remediation execution"),
    database_url: str = typer.Option("", "--database-url", help="Override database URL"),
) -> None:
    """Start database access, runtime, scanner tasks and FastAPI/Uvicorn in foreground."""
    loaded = load_config(config)
    fastapi_app, _ = create_app_from_config(loaded, apply=apply, database_url=database_url)
    uvicorn.run(fastapi_app, host=loaded.api.host, port=loaded.api.port)


app.command(name="health")(commands.health)
app.command(name="status")(commands.status)
app.command(name="scanners")(commands.scanners)
app.command(name="incidents")(commands.incidents)
app.command(name="incident")(commands.incident)


if __name__ == "__main__":
    app()
