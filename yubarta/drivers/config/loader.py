from typing import Type, TypeVar

import yaml
from pydantic import ValidationError

from .models import FullConfig

# Generic TypeVar for the Pydantic model
T = TypeVar("T", bound=FullConfig)  # Bound to FullConfig or a common base if more models


def load_config_from_yaml(file_path: str, model: Type[T] = FullConfig) -> T:
    """
    Loads a YAML file from the given path, parses it into the specified Pydantic model,
    validates the structure, and returns the parsed object.

    Args:
        file_path: Path to the YAML configuration file.
        model: The Pydantic model to parse into (defaults to FullConfig).

    Returns:
        An instance of the Pydantic model with the loaded and validated data.

    Raises:
        FileNotFoundError: If the YAML file does not exist at the given path.
        yaml.YAMLError: If the YAML file is malformed or cannot be parsed.
        ValidationError: If the YAML content does not match the Pydantic model schema.
                         The error will contain detailed information about mismatches.
    """
    try:
        with open(file_path) as f:
            raw_data = yaml.safe_load(f)
    except FileNotFoundError:
        raise
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Error parsing YAML data from file: {file_path}\n{e}")

    if raw_data is None:
        pass  # Let Pydantic handle validation of None data if it's not valid for the model

    try:
        parsed_config = model.model_validate(raw_data)
        return parsed_config
    except ValidationError:
        raise
