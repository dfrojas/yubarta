from collections.abc import Callable
from contextlib import ExitStack
from typing import Any

import pytest
from fastapi.testclient import TestClient

from yubarta.incident.models import IncidentState
from yubarta.ingestion.schemas import RejectionReason
from yubarta.inventory.dependencies import get_inventory
from yubarta.inventory.schema import Inventory, Target
from yubarta.main import app

pytestmark = pytest.mark.integration

WEBHOOK_URL = "/api/v1/webhook/alertmanager"

JAVA_APP_LABELS = {"service": "java-app", "role": "api"}
UNKNOWN_LABELS = {"service": "ghost-service", "role": "nowhere"}


def target(address: str, labels: dict[str, str]) -> Target:
    return Target(address=address, labels=labels, credential="sops://secrets/x.yaml#ssh_key")


UNIQUE_MATCH_INVENTORY = Inventory(
    targets={
        "java-app-1": target("10.0.0.20", JAVA_APP_LABELS),
        "redis-cache-1": target("10.0.0.5", {"service": "redis", "role": "cache"}),
    }
)

AMBIGUOUS_INVENTORY = Inventory(
    targets={
        "java-app-1": target("10.0.0.20", JAVA_APP_LABELS),
        "java-app-2": target("10.0.0.21", JAVA_APP_LABELS),
    }
)


def alert(labels: dict[str, str], starts_at: str = "2026-07-30T12:00:00Z") -> dict[str, Any]:
    return {
        "status": "firing",
        "labels": {"alertname": "DiskFull", "instance": "server1", **labels},
        "annotations": {"summary": "Disk is full"},
        "startsAt": starts_at,
        "endsAt": "0001-01-01T00:00:00Z",
        "fingerprint": "abc123",
    }


def payload(*alerts: dict[str, Any]) -> dict[str, Any]:
    return {"receiver": "webhook", "status": "firing", "alerts": list(alerts)}


@pytest.fixture()
def client_factory(unit_of_work):
    """Build a client over a chosen inventory, against freshly truncated tables.

    The app's own lifespan builds the engine, so these tests exercise the real
    dependency wiring rather than a store injected past it.
    """
    with ExitStack() as stack:

        def build(inventory: Inventory) -> TestClient:
            app.dependency_overrides[get_inventory] = lambda: inventory
            client: TestClient = stack.enter_context(TestClient(app))
            return client

        yield build
    app.dependency_overrides.clear()


@pytest.fixture()
def client(client_factory: Callable[[Inventory], TestClient]) -> TestClient:
    return client_factory(UNIQUE_MATCH_INVENTORY)


def test_matching_alert_opens_one_received_incident(client):
    response = client.post(WEBHOOK_URL, json=payload(alert(JAVA_APP_LABELS)))

    assert response.status_code == 202
    body = response.json()
    assert body["rejected"] == []
    assert len(body["accepted"]) == 1
    accepted = body["accepted"][0]
    assert accepted["target_name"] == "java-app-1"
    assert accepted["state"] == IncidentState.received
    assert accepted["incident_id"]


def test_created_incident_is_readable_back_from_postgres(client):
    accepted = client.post(WEBHOOK_URL, json=payload(alert(JAVA_APP_LABELS))).json()["accepted"][0]

    read_back = client.get(f"/api/v1/incidents/{accepted['incident_id']}")

    assert read_back.status_code == 200
    incident = read_back.json()["incident"]
    assert incident["state"] == IncidentState.received
    assert incident["target_name"] == "java-app-1"
    assert incident["signal"]["labels"]["service"] == "java-app"
    assert incident["version"] == 0


def test_empty_alerts_list_is_accepted_and_creates_nothing(client):
    response = client.post(WEBHOOK_URL, json=payload())

    assert response.status_code == 202
    assert response.json() == {"accepted": [], "rejected": []}
    assert client.get("/api/v1/incidents").json() == []


def test_redelivery_returns_the_same_incident_and_creates_no_second_row(client):
    first = client.post(WEBHOOK_URL, json=payload(alert(JAVA_APP_LABELS)))
    second = client.post(WEBHOOK_URL, json=payload(alert(JAVA_APP_LABELS)))

    assert second.status_code == 202
    first_id = first.json()["accepted"][0]["incident_id"]
    assert second.json()["accepted"][0]["incident_id"] == first_id
    assert len(client.get("/api/v1/incidents").json()) == 1


def test_alert_matching_no_target_is_rejected_without_creating_an_incident(client):
    response = client.post(WEBHOOK_URL, json=payload(alert(UNKNOWN_LABELS)))

    assert response.status_code == 202
    body = response.json()
    assert body["accepted"] == []
    assert body["rejected"][0]["reason"] == RejectionReason.no_matching_target
    assert client.get("/api/v1/incidents").json() == []


def test_fully_unresolvable_payload_is_still_accepted(client):
    response = client.post(
        WEBHOOK_URL,
        json=payload(
            alert(UNKNOWN_LABELS, starts_at="2026-07-30T12:00:00Z"),
            alert(UNKNOWN_LABELS, starts_at="2026-07-30T12:05:00Z"),
        ),
    )

    assert response.status_code == 202
    body = response.json()
    assert body["accepted"] == []
    assert len(body["rejected"]) == 2
    assert client.get("/api/v1/incidents").json() == []


def test_deduplication_does_not_depend_on_process_local_state(unit_of_work):
    """The closest thing to a restart without spawning a process.

    Each `TestClient` runs the app's lifespan, so the second one has its own engine
    and connection pool and carries nothing over in memory. If deduplication lived in
    a process-local dict, as it did before this stage, the second delivery would open
    a second incident.
    """
    app.dependency_overrides[get_inventory] = lambda: UNIQUE_MATCH_INVENTORY
    redelivered = payload(alert(JAVA_APP_LABELS))
    try:
        with TestClient(app) as first_process:
            first_id = first_process.post(WEBHOOK_URL, json=redelivered).json()["accepted"][0]["incident_id"]

        with TestClient(app) as second_process:
            body = second_process.post(WEBHOOK_URL, json=redelivered).json()
            assert body["accepted"][0]["incident_id"] == first_id
            assert len(second_process.get("/api/v1/incidents").json()) == 1
    finally:
        app.dependency_overrides.clear()


def test_alert_matching_several_targets_is_rejected_naming_the_candidates(client_factory):
    client = client_factory(AMBIGUOUS_INVENTORY)

    response = client.post(WEBHOOK_URL, json=payload(alert(JAVA_APP_LABELS)))

    assert response.status_code == 202
    rejected = response.json()["rejected"][0]
    assert rejected["reason"] == RejectionReason.ambiguous_target
    assert "java-app-1" in rejected["detail"]
    assert "java-app-2" in rejected["detail"]
    assert client.get("/api/v1/incidents").json() == []


def test_mixed_payload_creates_incidents_only_for_resolvable_alerts(client):
    response = client.post(
        WEBHOOK_URL,
        json=payload(alert(JAVA_APP_LABELS), alert(UNKNOWN_LABELS)),
    )

    assert response.status_code == 202
    body = response.json()
    assert len(body["accepted"]) == 1
    assert len(body["rejected"]) == 1
    assert body["accepted"][0]["target_name"] == "java-app-1"
    assert len(client.get("/api/v1/incidents").json()) == 1


def test_two_distinct_alerts_open_two_incidents(client):
    response = client.post(
        WEBHOOK_URL,
        json=payload(
            alert(JAVA_APP_LABELS, starts_at="2026-07-30T12:00:00Z"),
            alert(JAVA_APP_LABELS, starts_at="2026-07-30T12:05:00Z"),
        ),
    )

    accepted = response.json()["accepted"]
    assert len({entry["incident_id"] for entry in accepted}) == 2
    assert len(client.get("/api/v1/incidents").json()) == 2
