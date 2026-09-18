"""Single executable: `yubarta`. `serve` starts DB + runtime + scanners + FastAPI."""

from __future__ import annotations

import typer
import uvicorn

from yubarta.api import create_app_from_config
from yubarta.config import load_config

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


# Re-export HTTP-client commands so `yubarta status` etc. work on the same binary.
from yubarta.cli import health as _health  # noqa: E402
from yubarta.cli import incident as _incident  # noqa: E402
from yubarta.cli import incidents as _incidents  # noqa: E402
from yubarta.cli import scanners as _scanners  # noqa: E402
from yubarta.cli import status as _status  # noqa: E402

app.command(name="health")(_health)
app.command(name="status")(_status)
app.command(name="scanners")(_scanners)
app.command(name="incidents")(_incidents)
app.command(name="incident")(_incident)


if __name__ == "__main__":
    app()
