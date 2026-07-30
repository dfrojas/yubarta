from datetime import datetime, timedelta, timezone

import pytest

from yubarta.domain.signal import Signal, SignalSource, SignalStatus
from yubarta.incident.models import AttemptOutcome, IncidentState
from yubarta.incident.routes.incidents import DEFAULT_LIST_LIMIT

pytestmark = pytest.mark.integration

BASE_TIME = datetime(2026, 7, 30, 12, 0, 0, tzinfo=timezone.utc)


def make_signal(minutes_offset: int = 0, labels: dict[str, str] | None = None) -> Signal:
    return Signal(
        status=SignalStatus.firing,
        source=SignalSource.webhook,
        labels=labels or {"service": "java-app", "role": "api"},
        fired_at=BASE_TIME + timedelta(minutes=minutes_offset),
        raw={"alertname": "DiskFull"},
    )


async def test_reading_a_known_incident_returns_state_attempts_and_log(api_client, incident_store):
    incident = await incident_store.create(make_signal(), "java-app-1")
    await incident_store.transition(
        incident.id,
        IncidentState.diagnosing,
        expected_version=incident.version,
        lease_generation=incident.lease_generation,
    )
    attempt = await incident_store.record_attempt(incident.id, "restart-java-app")
    await incident_store.complete_attempt(attempt.id, AttemptOutcome.succeeded, {"exit_code": 0})

    response = api_client.get(f"/api/v1/incidents/{incident.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["incident"]["state"] == IncidentState.diagnosing
    assert body["incident"]["version"] == 1
    assert len(body["incident"]["attempts"]) == 1
    assert body["incident"]["attempts"][0]["outcome"] == AttemptOutcome.succeeded
    assert [entry["to_state"] for entry in body["transitions"]] == [IncidentState.diagnosing]


async def test_reading_an_unknown_incident_returns_404(api_client):
    response = api_client.get("/api/v1/incidents/does-not-exist")

    assert response.status_code == 404
    assert "does-not-exist" in response.json()["detail"]


async def test_list_is_bounded_by_default(api_client, incident_store):
    for offset in range(DEFAULT_LIST_LIMIT + 1):
        await incident_store.create(make_signal(offset), "java-app-1")

    response = api_client.get("/api/v1/incidents")

    assert response.status_code == 200
    assert len(response.json()) == DEFAULT_LIST_LIMIT


async def test_list_honours_an_explicit_limit(api_client, incident_store):
    for offset in range(3):
        await incident_store.create(make_signal(offset), "java-app-1")

    response = api_client.get("/api/v1/incidents", params={"limit": 2})

    assert len(response.json()) == 2


async def test_list_rejects_a_limit_outside_the_allowed_range(api_client):
    assert api_client.get("/api/v1/incidents", params={"limit": 0}).status_code == 422
    assert api_client.get("/api/v1/incidents", params={"limit": 500}).status_code == 422


async def test_list_filters_by_target_name(api_client, incident_store):
    await incident_store.create(make_signal(0), "java-app-1")
    await incident_store.create(make_signal(5, {"service": "redis", "role": "cache"}), "redis-cache-1")

    response = api_client.get("/api/v1/incidents", params={"target_name": "redis-cache-1"})

    body = response.json()
    assert len(body) == 1
    assert body[0]["target_name"] == "redis-cache-1"


async def test_list_is_most_recent_first(api_client, incident_store):
    older = await incident_store.create(make_signal(0), "java-app-1")
    newer = await incident_store.create(make_signal(5), "java-app-1")

    body = api_client.get("/api/v1/incidents").json()

    assert [entry["id"] for entry in body] == [newer.id, older.id]
