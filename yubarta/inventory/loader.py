from pathlib import Path

import yaml

from yubarta.inventory.schema import Inventory


def load_inventory(path: str | Path) -> Inventory:
    with open(path) as f:
        raw = yaml.safe_load(f)
    return Inventory.model_validate(raw)
