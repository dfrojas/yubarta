from urllib.parse import urljoin

import requests
import typer
import yaml

app = typer.Typer()

API_URL = "http://localhost:8000"  # Default API URL


@app.command()
def apply(
    yaml_file: typer.FileText = typer.Argument(
        ..., help="Path to the eBPF deployment YAML file"
    ),
    api_url: str = typer.Option(API_URL, help="URL of the API server"),
):
    """Apply an eBPF deployment YAML file."""
    try:
        yaml_content = yaml.safe_load(yaml_file)
        namespace = yaml_content["metadata"].get("namespace", "default")

        response = requests.post(
            urljoin(api_url, f"/api/v1/namespaces/{namespace}/ebpfdeployments"),
            json=yaml_content,
        )
        response.raise_for_status()
        result = response.json()
        typer.echo(f"Deployment created successfully. Reference: {result['reference']}")
    except yaml.YAMLError as e:
        typer.echo(f"Error parsing YAML file: {str(e)}", err=True)
    except requests.RequestException as e:
        typer.echo(f"Error communicating with API server: {str(e)}", err=True)
    except Exception as e:
        typer.echo(f"Unexpected error: {str(e)}", err=True)


@app.command()
def get(
    name: str,
    namespace: str = typer.Option("default", help="Namespace of the deployment"),
    api_url: str = typer.Option(API_URL, help="URL of the API server"),
):
    """Get details of an eBPF deployment."""
    try:
        response = requests.get(
            urljoin(api_url, f"/api/v1/namespaces/{namespace}/ebpfdeployments/{name}")
        )
        response.raise_for_status()
        deployment = response.json()
        typer.echo(yaml.dump(deployment, default_flow_style=False))
    except requests.RequestException as e:
        typer.echo(f"Error communicating with API server: {str(e)}", err=True)
    except Exception as e:
        typer.echo(f"Unexpected error: {str(e)}", err=True)


@app.command()
def list(
    namespace: str = typer.Option("default", help="Namespace of the deployments"),
    api_url: str = typer.Option(API_URL, help="URL of the API server"),
):
    """List all eBPF deployments in a namespace."""
    try:
        response = requests.get(
            urljoin(api_url, f"/api/v1/namespaces/{namespace}/ebpfdeployments")
        )
        response.raise_for_status()
        deployments = response.json()
        typer.echo(yaml.dump(deployments, default_flow_style=False))
    except requests.RequestException as e:
        typer.echo(f"Error communicating with API server: {str(e)}", err=True)
    except Exception as e:
        typer.echo(f"Unexpected error: {str(e)}", err=True)
