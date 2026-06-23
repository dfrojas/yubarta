import pytest
from fastapi.testclient import TestClient

from yubarta.ingestion.dependencies import get_signal_store
from yubarta.ingestion.store import InMemorySignalStore
from yubarta.main import app

FIRING_PAYLOAD = {
    "receiver": "webhook",
    "status": "firing",
    "alerts": [
        {
            "status": "firing",
            "labels": {"alertname": "DiskFull", "instance": "server1"},
            "annotations": {},
            "startsAt": "2026-01-01T12:00:00Z",
            "endsAt": "0001-01-01T00:00:00Z",
            "fingerprint": "abc123",
        }
    ],
}


@pytest.fixture()
def client():
    store = InMemorySignalStore()
    app.dependency_overrides[get_signal_store] = lambda: store
    with TestClient(app) as c:
        yield c, store
    app.dependency_overrides.clear()


def test_valid_payload_returns_202_with_signal_ids(client):
    c, _ = client
    resp = c.post("/api/v1/webhook/alertmanager", json=FIRING_PAYLOAD)
    assert resp.status_code == 202
    body = resp.json()
    assert "signal_ids" in body
    assert len(body["signal_ids"]) == 1


def test_empty_alerts_list_returns_202(client):
    c, _ = client
    payload = {**FIRING_PAYLOAD, "alerts": []}
    resp = c.post("/api/v1/webhook/alertmanager", json=payload)
    assert resp.status_code == 202
    assert resp.json()["signal_ids"] == []


def test_duplicate_submission_returns_202_without_double_store(client):
    c, store = client
    c.post("/api/v1/webhook/alertmanager", json=FIRING_PAYLOAD)
    resp = c.post("/api/v1/webhook/alertmanager", json=FIRING_PAYLOAD)
    assert resp.status_code == 202
    signal_id = resp.json()["signal_ids"][0]
    assert len(store._store) == 1
    assert signal_id in store._store


def test_store_override_is_isolated_per_test(client):
    c, store = client
    assert len(store._store) == 0
    c.post("/api/v1/webhook/alertmanager", json=FIRING_PAYLOAD)
    assert len(store._store) == 1
