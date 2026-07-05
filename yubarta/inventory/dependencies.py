from functools import lru_cache

from yubarta.config import settings
from yubarta.inventory.loader import load_inventory
from yubarta.inventory.schema import Inventory


@lru_cache
def get_inventory() -> Inventory:
    return load_inventory(settings.INVENTORY_PATH)
