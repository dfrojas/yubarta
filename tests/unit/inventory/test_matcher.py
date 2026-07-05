from datetime import datetime, timezone

import pytest

from yubarta.domain.signal import Signal, SignalSource, SignalStatus
from yubarta.inventory.matcher import AmbiguousTargetError, NoMatchingTargetError, match_target
from yubarta.inventory.schema import Inventory, Target


def make_signal(labels: dict[str, str]) -> Signal:
    return Signal(
        status=SignalStatus.firing,
        source=SignalSource.webhook,
        labels=labels,
        fired_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        raw={},
    )


def make_target(labels: dict[str, str]) -> Target:
    return Target(address="10.0.0.1", labels=labels, credential="sops://x#y")


def test_unique_match_returns_the_target():
    inventory = Inventory(
        targets={
            "java-app-1": make_target({"service": "java-app"}),
            "redis-cache-1": make_target({"service": "redis"}),
        }
    )
    signal = make_signal({"service": "java-app", "severity": "critical"})
    assert match_target(inventory, signal) is inventory.targets["java-app-1"]


def test_no_match_raises_no_matching_target_error():
    inventory = Inventory(targets={"redis-cache-1": make_target({"service": "redis"})})
    signal = make_signal({"service": "java-app"})
    with pytest.raises(NoMatchingTargetError):
        match_target(inventory, signal)


def test_ambiguous_match_raises_with_all_candidates():
    inventory = Inventory(
        targets={
            "java-app-1": make_target({"service": "java-app"}),
            "java-app-2": make_target({"service": "java-app"}),
        }
    )
    signal = make_signal({"service": "java-app"})
    with pytest.raises(AmbiguousTargetError) as exc_info:
        match_target(inventory, signal)
    assert set(exc_info.value.candidates) == {"java-app-1", "java-app-2"}


def test_extra_signal_labels_do_not_block_a_match():
    inventory = Inventory(targets={"java-app-1": make_target({"service": "java-app", "role": "api"})})
    signal = make_signal({"service": "java-app", "role": "api", "alertname": "DiskFull", "instance": "server1"})
    assert match_target(inventory, signal) is inventory.targets["java-app-1"]
