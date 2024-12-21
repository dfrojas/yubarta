from http import HTTPStatus

import requests
import typer
import yaml

from engine.conf import settings

app = typer.Typer()


@app.command()
def apply(config_file: str):
    """Apply a configuration file"""
    with open(config_file) as file:
        config_data = yaml.safe_load(file)

    # Siempre pasamos por el API server
    response = requests.post(f"{settings.API_URL}/api/v1/deployments", json=config_data)

    if response.status_code == HTTPStatus.OK:
        typer.echo("Successfully applied configuration")
    else:
        typer.echo(f"Error: {response.content}")
