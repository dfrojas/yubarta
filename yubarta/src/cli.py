import click
import requests

@click.command()
@click.argument('yaml_file', type=click.File('r'))
@click.option('--api-url', default='http://localhost:8000', help='URL of the eBPF deployment API')
def apply(yaml_file, api_url):
    """Apply an eBPF deployment YAML file."""
    yaml_content = yaml_file.read()
    response = requests.post(f"{api_url}/apply_yaml", data=yaml_content)
    if response.status_code == 200:
        click.echo(response.json()['message'])
    else:
        click.echo(f"Error: {response.json()['detail']}", err=True)

if __name__ == '__main__':
    apply()
