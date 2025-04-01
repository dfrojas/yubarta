from http import HTTPStatus

import requests
import typer
import yaml

from engine.conf import settings

app = typer.Typer()


@app.command()
def execute(config_file: str):
    """Execute a configuration file"""
    with open(config_file) as file:
        config_data = yaml.safe_load(file)
    response = requests.post(f"{settings.API_URL}/api/v1/execute", json=config_data)

    if response.status_code == HTTPStatus.OK:
        typer.echo("Successfully applied configuration")
    else:
        typer.echo(f"Error: {response.content}")


def check_requirements():
    """
    Iterate over all the machines in the deployment and check if the requirements are met (libbpf, clang, etc.)
    """
    pass
