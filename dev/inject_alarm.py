"""Drive the reactive path end-to-end against a raised stack.

Posts a fake Alertmanager alert, then reads the resulting incident back out of
Postgres through the API instead of echoing what was sent, so a green run means the
incident is really persisted and not just accepted.

Run it inside the api container (`make inject-alarm`), where the API is on localhost.
"""

import argparse
import sys
from datetime import datetime, timezone
from typing import Any

import httpx

DEFAULT_BASE_URL = "http://localhost:8080"
WEBHOOK_PATH = "/api/v1/webhook/alertmanager"
INCIDENTS_PATH = "/api/v1/incidents"

# Matches java-app-1 in the checked-in inventory.yaml (service + role).
MATCHING_LABELS = {"service": "java-app", "role": "api"}
# Matches nothing in it, to show the rejection path.
UNMATCHED_LABELS = {"service": "ghost-service", "role": "nowhere"}


def build_payload(labels: dict[str, str], fired_at: datetime, alertname: str) -> dict[str, Any]:
    return {
        "receiver": "yubarta",
        "status": "firing",
        "alerts": [
            {
                "status": "firing",
                "labels": {"alertname": alertname, "severity": "critical", **labels},
                "annotations": {"summary": f"{alertname} on {labels.get('service')}"},
                "startsAt": fired_at.isoformat().replace("+00:00", "Z"),
                "endsAt": "0001-01-01T00:00:00Z",
                "fingerprint": "deadbeefcafe",
            }
        ],
    }


def section(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


def post_alert(client: httpx.Client, payload: dict[str, Any]) -> dict[str, Any]:
    response = client.post(WEBHOOK_PATH, json=payload)
    if response.status_code != 202:
        raise RuntimeError(f"webhook returned {response.status_code}: {response.text}")
    body: dict[str, Any] = response.json()
    return body


def print_incident(client: httpx.Client, incident_id: str) -> None:
    response = client.get(f"{INCIDENTS_PATH}/{incident_id}")
    if response.status_code != 200:
        raise RuntimeError(f"reading incident {incident_id} returned {response.status_code}: {response.text}")
    detail = response.json()
    incident = detail["incident"]
    print(f"  id            {incident['id']}")
    print(f"  state         {incident['state']}")
    print(f"  target        {incident['target_name']}")
    print(f"  version       {incident['version']}")
    print(f"  lease gen     {incident['lease_generation']} (owner: {incident['lease_owner']})")
    print(f"  signal id     {incident['signal']['id']}")
    print(f"  fingerprint   {incident['signal']['fingerprint']}")
    print(f"  labels        {incident['signal']['labels']}")
    print(f"  created at    {incident['created_at']}")
    print(f"  attempts      {len(incident['attempts'])}")
    transitions = detail["transitions"]
    if transitions:
        walked = " -> ".join([transitions[0]["from_state"], *[entry["to_state"] for entry in transitions]])
        print(f"  lifecycle log {walked}")
    else:
        print("  lifecycle log (empty, nothing has driven this incident yet)")


def print_recent(client: httpx.Client, limit: int) -> None:
    response = client.get(INCIDENTS_PATH, params={"limit": limit})
    response.raise_for_status()
    incidents = response.json()
    print(f"  {len(incidents)} incident(s), most recent first:")
    for incident in incidents:
        print(
            f"  - {incident['id']}  {incident['state']:<12} {incident['target_name']:<16} "
            f"{incident['created_at']}"
        )


def run(client: httpx.Client, list_only: bool) -> None:
    if list_only:
        section("Recent incidents")
        print_recent(client, limit=20)
        return

    fired_at = datetime.now(timezone.utc).replace(microsecond=0)
    payload = build_payload(MATCHING_LABELS, fired_at, "DiskWillFillIn4Hours")

    section("1. Post a firing alert that matches a target in inventory.yaml")
    print(f"  labels: {MATCHING_LABELS}")
    accepted = post_alert(client, payload)["accepted"]
    if not accepted:
        raise RuntimeError("the alert was not accepted, check that inventory.yaml still defines java-app-1")
    incident_id = accepted[0]["incident_id"]
    print(f"  202 Accepted, incident {incident_id} opened on {accepted[0]['target_name']}")

    section("2. Read the incident back out of Postgres")
    print_incident(client, incident_id)

    section("3. Redeliver the same alert (Alertmanager repeats itself)")
    redelivered = post_alert(client, payload)["accepted"]
    if redelivered[0]["incident_id"] != incident_id:
        raise RuntimeError(
            f"redelivery created a second incident ({redelivered[0]['incident_id']}), deduplication is broken"
        )
    print(f"  202 Accepted, same incident {incident_id}, no duplicate created")
    print("  deduplication comes from the unique constraint on incidents.signal_id, so it survives a restart")

    section("4. Post an alert that matches no target")
    print(f"  labels: {UNMATCHED_LABELS}")
    unmatched = post_alert(client, build_payload(UNMATCHED_LABELS, fired_at, "GhostAlert"))
    if unmatched["accepted"] or not unmatched["rejected"]:
        raise RuntimeError(f"expected a rejection, got {unmatched}")
    rejection = unmatched["rejected"][0]
    print(f"  202 Accepted, rejected as {rejection['reason']}: {rejection['detail']}")
    print("  still a 2xx on purpose: a retry cannot fix missing inventory coverage")

    section("5. Recent incidents")
    print_recent(client, limit=20)

    print("\nDone. Nothing drives this incident further yet: the Director (stage 4) does not exist.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject a fake alarm and follow it through the system")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help=f"API base URL (default {DEFAULT_BASE_URL})")
    parser.add_argument("--list-only", action="store_true", help="only list recent incidents")
    arguments = parser.parse_args()

    try:
        with httpx.Client(base_url=arguments.base_url, timeout=10.0) as client:
            run(client, arguments.list_only)
    except (httpx.HTTPError, RuntimeError) as error:
        print(f"\nFAILED: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
