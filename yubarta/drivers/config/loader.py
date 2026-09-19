import os
import re
from pathlib import Path

import yaml

from yubarta.config.settings import AppConfig
from yubarta.drivers.config.config_schemas import ConfigInput


def expand_env_vars(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        value = os.environ.get(name)
        if value is None:
            raise ValueError(f"Missing required environment variable: {name}")
        return value

    return re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", replace, text)


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    with config_path.open() as source:
        text = source.read()
    try:
        data = yaml.safe_load(expand_env_vars(text))
        config = ConfigInput.model_validate(data).normalized()
    except (ValueError, yaml.YAMLError) as exc:
        raise ValueError(f"Invalid configuration {config_path}: {exc}") from exc
    if not config.database_url:
        config.database_url = os.environ.get("YUBARTA_DATABASE_URL", "")
    return config
