from yubarta.domain.signal import Signal
from yubarta.inventory.schema import Inventory, Target


class InventoryMatchError(Exception):
    pass


class NoMatchingTargetError(InventoryMatchError):
    pass


class AmbiguousTargetError(InventoryMatchError):
    def __init__(self, candidates: list[str]) -> None:
        self.candidates = candidates
        super().__init__(f"ambiguous target match: {candidates}")


def match_target(inventory: Inventory, signal: Signal) -> Target:
    matches = {
        name: target for name, target in inventory.targets.items() if target.labels.items() <= signal.labels.items()
    }
    if not matches:
        raise NoMatchingTargetError(f"no target matches labels {signal.labels}")
    if len(matches) > 1:
        raise AmbiguousTargetError(sorted(matches.keys()))
    return next(iter(matches.values()))
