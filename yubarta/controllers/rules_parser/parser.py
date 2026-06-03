"""
This module contains the main parsing logic for reading and validating rule files.
"""

from typing import List

import yaml
from pydantic import ValidationError

from .exceptions import RuleParsingError
from .models import Rule


def parse_rules(file_path: str) -> List[Rule]:
    """
    Reads a YAML rule file, validates it against the Pydantic models, and returns a list of Rule objects.

    Args:
        file_path: The path to the YAML rule file.

    Returns:
        A list of validated Rule objects.

    Raises:
        FileNotFoundError: If the file is not found at the specified path.
        RuleParsingError: If the YAML file has an incorrect structure or if any rule
                          fails Pydantic validation, with a detailed error message.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"The rules file was not found at path: {file_path}")

    if not isinstance(data, dict) or "rules" not in data:
        raise RuleParsingError("The YAML file must contain a top-level 'rules' key with a list of rules.")

    validated_rules: List[Rule] = []

    for i, rule_dict in enumerate(data["rules"]):
        rule_name = rule_dict.get("name", f"unnamed_rule_at_index_{i}")
        try:
            # Pydantic performs recursive validation here
            rule = Rule(**rule_dict)
            validated_rules.append(rule)
        except (ValidationError, ValueError) as e:
            # Catches both Pydantic validation errors and our custom logic errors
            # and raises a new exception with a clearer, more contextual message.
            error_message = f"Validation error in rule '{rule_name}': {e}"
            raise RuleParsingError(error_message) from e

    return validated_rules
