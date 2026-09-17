from datetime import datetime, timezone

from yubarta.domain.signal import Signal, SignalSource, SignalStatus


def make_signal(**overrides) -> Signal:
    defaults = {
        "status": SignalStatus.firing,
        "source": SignalSource.webhook,
        "labels": {"service": "java-app", "env": "prod"},
        "fired_at": datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        "raw": {"alert": "DiskFull"},
    }
    return Signal(**(defaults | overrides))


def test_id_is_deterministic():
    a = make_signal()
    b = make_signal()
    assert a.id == b.id


def test_fingerprint_excludes_fired_at():
    t1 = make_signal(fired_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    t2 = make_signal(fired_at=datetime(2026, 6, 1, tzinfo=timezone.utc))
    assert t1.fingerprint == t2.fingerprint


def test_resolved_carries_same_fingerprint_as_firing():
    firing = make_signal(status=SignalStatus.firing)
    resolved = make_signal(status=SignalStatus.resolved)
    assert firing.fingerprint == resolved.fingerprint


def test_different_labels_produce_different_fingerprints():
    a = make_signal(labels={"service": "redis"})
    b = make_signal(labels={"service": "java-app"})
    assert a.fingerprint != b.fingerprint


def test_signal_has_no_source_specific_fields():
    signal = make_signal()
    assert not hasattr(signal, "group_id")
    assert not hasattr(signal, "topic")
    assert not hasattr(signal, "lag")
