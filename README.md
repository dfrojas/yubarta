# Yubarta (y5a)

<img src="docs/img/yubarta_whale_logo.png" width="150">

----


Yubarta is an application for deploying eBPF programs. It provides a simple and efficient way to manage eBPF deployments through a RESTful API and a command-line interface.

## Features

- Deploy eBPF programs to target machines
- RESTful API for programmatic deployments
- Command-line interface for easy management
- YAML-based configuration for eBPF deployments

## Installation

Yubarta uses Poetry for dependency management. To install the project, follow these steps:

1. Clone the repository:
   ```
   git clone https://github.com/dfrojas/yubarta.git
   cd yubarta
   ```

2. Install dependencies using Poetry:
   ```
   poetry install
   ```

## Usage

### API Server

To start the API server, run:

```
poetry run yubarta-api
```

The server will start on `http://0.0.0.0:8000`.

### Command-line Interface

To use the CLI, run:

```
poetry run yubarta-cli apply <path_to_yaml_file>
```

You can specify a custom API URL using the `--api-url` option:

```
poetry run yubarta-cli apply <path_to_yaml_file> --api-url http://custom-api-url:8000
```

## Configuration

Yubarta uses YAML files for configuring eBPF deployments. The YAML file should contain the eBPF program code and target machine details.

## Development

To set up the development environment:

1. Install development dependencies:
   ```
   poetry install --dev
   ```

2. Run tests:
   ```
   poetry run pytest
   ```

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Authors

- Diego Fernando Rojas <hello@dfrojas.com>

For more information, visit the [Yubarta GitHub repository](https://github.com/dfrojas/yubarta).