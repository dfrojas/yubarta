from typing import Any

from pydantic import BaseModel, model_validator


class InventoryGroup(BaseModel):
    transport: str
    user: str
    port: int


class ScanConfig(BaseModel):
    interval: str | None = None
    commands: list[dict[str, Any]] = []
    checks: list[str] = []


class Target(BaseModel):
    group: str | None = None
    address: str
    labels: dict[str, str]
    scan: ScanConfig | None = None
    credential: str
    remediations: list[str] = []
    transport: str | None = None
    user: str | None = None
    port: int | None = None


class Inventory(BaseModel):
    groups: dict[str, InventoryGroup] = {}
    targets: dict[str, Target]

    @model_validator(mode="after")
    def _merge_group_defaults(self) -> "Inventory":
        """Fill each target's transport/user/port from its referenced group, if unset.

        Raises a validation error if a target references a group that doesn't exist,
        so an unresolved group reference fails at load time rather than at connection time.
        """
        for name, target in self.targets.items():
            if target.group is None:
                continue
            if target.group not in self.groups:
                raise ValueError(f"target '{name}' references unknown group '{target.group}'")
            group = self.groups[target.group]
            target.transport = target.transport or group.transport
            target.user = target.user or group.user
            target.port = target.port or group.port
        return self
