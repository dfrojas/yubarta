import os
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import SecretStr, ValidationError

from yubarta.config.settings import AppConfig, Environment, HTTPCheck
from yubarta.core.errors import ConfigurationError
from yubarta.drivers.config.config_schemas import ConfigInput


def required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ConfigurationError(f"Required environment variable is missing or empty: {name}")
    return value


def expand(value: Any) -> Any:
    if isinstance(value, str):
        return re.sub(r"\$\{([A-Za-z_][A-Za-z_0-9]*)\}", lambda match: required_env(match[1]), value)
    if isinstance(value, list):
        return [expand(item) for item in value]
    if isinstance(value, dict):
        return {key: expand(item) for key, item in value.items()}
    return value


def load_config(path: Path) -> AppConfig:
    try:
        with path.open() as stream:
            data = expand(yaml.safe_load(stream))
        if not isinstance(data, dict):
            raise ConfigurationError("Expected a YAML mapping")
        environment = Environment(**({"database_url": data["database_url"]} if "database_url" in data else {}))
        data.setdefault("database_url", environment.database_url)
        api = data.setdefault("api", {})
        if environment.api_token and isinstance(api, dict):
            api.setdefault("token", environment.api_token)
        config = ConfigInput.model_validate(data)
        checks = []
        for check in config.checks:
            if isinstance(check, HTTPCheck):
                headers = {name: SecretStr(required_env(variable)) for name, variable in check.auth.headers_from_env.items()}
                if check.auth.bearer_from_env:
                    headers["Authorization"] = SecretStr(f"Bearer {required_env(check.auth.bearer_from_env)}")
                check = check.model_copy(update={"headers": headers})
            checks.append(check)
        return config.model_copy(update={"checks": checks})
    except ValidationError as error:
        messages = [f"{'.'.join(map(str, item['loc']))}: {item['msg']}" for item in error.errors(include_input=False)]
        raise ConfigurationError(f"{path}: {'; '.join(messages)}") from None
    except (OSError, yaml.YAMLError, ConfigurationError) as error:
        raise ConfigurationError(f"{path}: {error}") from error
