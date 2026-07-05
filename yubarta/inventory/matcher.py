from yubarta.domain.signal import Signal
from yubarta.inventory.schema import Inventory, Target


class InventoryMatchError(Exception):
    pass


class NoMatchingTargetError(InventoryMatchError):
    pass


class AmbiguousTargetError(InventoryMatchError):
    """Raised when a signal matches more than one target.

    Example: two targets in inventory.yaml with the same labels

        targets:
          java-app-1:
            labels:
              service: java-app
          java-app-2:
            labels:
              service: java-app

    and an incoming alert

        alerts:
          - labels:
              service: java-app
              severity: critical

    A target matches whenever all of its labels are also present on the
    signal. Both java-app-1 and java-app-2 qualify here, so nothing
    distinguishes which host the signal is about.
    """

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
