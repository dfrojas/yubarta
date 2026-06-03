"""
This module defines the Pydantic models for validating the structure of a rule.
"""

from typing import List, Literal, Optional, Union

from pydantic import BaseModel, model_validator


class Remediation(BaseModel):
    """
    Defines a remediation action, including the script to run and its arguments.
    """

    script: str
    args: List[str] = []


class Threshold(BaseModel):
    """
    Defines the threshold for a metric. Can be 'absolute' or 'dynamic_growth'.
    """

    type: Literal["absolute", "dynamic_growth"]
    value: Optional[Union[int, float]] = None
    factor: Optional[Union[int, float]] = None

    @model_validator(mode="after")
    def check_value_or_factor_based_on_type(self) -> "Threshold":
        """
        Custom validator to ensure consistency between the threshold type and the provided fields.
        """
        # Business logic: If type is 'absolute', the 'value' field is required.
        if self.type == "absolute" and self.value is None:
            raise ValueError("For a threshold of type 'absolute', the 'value' field is required.")

        # Business logic: If type is 'dynamic_growth', the 'factor' field is required.
        if self.type == "dynamic_growth" and self.factor is None:
            raise ValueError("For a threshold of type 'dynamic_growth', the 'factor' field is required.")

        return self


class Rule(BaseModel):
    """
    Defines a complete rule, including its name, metric, threshold, severity, and remediation action.
    """

    name: str
    metric: str
    threshold: Threshold
    severity: Literal["WARNING", "CRITICAL"]
    remediation: Remediation
