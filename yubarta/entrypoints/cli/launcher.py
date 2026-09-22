import logging
from pathlib import Path
from typing import Annotated

import typer
import uvicorn

from yubarta.core.errors import ConfigurationError
from yubarta.drivers.config.loader import load_config
from yubarta.entrypoints.api_server.app import create_app
from yubarta.entrypoints.cli.commands import app
from yubarta.runtime import YubartaRuntime


@app.command()
def serve(config: Annotated[Path, typer.Option(exists=True, dir_okay=False)],
          apply: Annotated[bool, typer.Option("--apply")] = False) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    try:
        settings = load_config(config)
    except ConfigurationError as error:
        raise typer.BadParameter(str(error)) from error
    runtime = YubartaRuntime(settings, apply)
    uvicorn.run(create_app(runtime), host=settings.api.host, port=settings.api.port,
                timeout_graceful_shutdown=int(settings.shutdown_timeout + 10))
