from yubarta.domain.signal import SignalSource, SignalStatus
from yubarta.ingestion.normalizers.alertmanager import normalize_alertmanager

FIRING_ALERT = {
    "status": "firing",
    "labels": {"alertname": "DiskFull", "instance": "server1"},
    "annotations": {"summary": "Disk is full"},
    "startsAt": "2026-01-01T12:00:00Z",
    "endsAt": "0001-01-01T00:00:00Z",
    "fingerprint": "abc123def456",
}

RESOLVED_ALERT = {**FIRING_ALERT, "status": "resolved"}


def alertmanager_payload(*alerts: dict) -> dict:
    return {"receiver": "webhook", "status": "firing", "alerts": list(alerts)}


def test_single_firing_alert_is_normalized():
    signals = normalize_alertmanager(alertmanager_payload(FIRING_ALERT))
    assert len(signals) == 1
    s = signals[0]
    assert s.status == SignalStatus.firing
    assert s.source == SignalSource.webhook
    assert s.labels == FIRING_ALERT["labels"]
    assert s.raw == FIRING_ALERT


def test_resolved_alert_sets_correct_status():
    signals = normalize_alertmanager(alertmanager_payload(RESOLVED_ALERT))
    assert signals[0].status == SignalStatus.resolved


def test_multiple_alerts_produce_multiple_signals():
    payload = alertmanager_payload(FIRING_ALERT, RESOLVED_ALERT, FIRING_ALERT)
    assert len(normalize_alertmanager(payload)) == 3


def test_signal_id_is_deterministic():
    signals_a = normalize_alertmanager(alertmanager_payload(FIRING_ALERT))
    signals_b = normalize_alertmanager(alertmanager_payload(FIRING_ALERT))
    assert signals_a[0].id == signals_b[0].id


def test_empty_alerts_list_returns_empty():
    assert normalize_alertmanager({"alerts": []}) == []
