# Capability: Signal Ingestion

## Purpose

Accepts alerts from external monitoring systems and turns them into canonical `Signal`
objects, then opens one incident per signal that resolves to a target.

Detection stays deterministic: this capability decides nothing about whether something is
wrong, it only normalizes what an external system already decided and records it durably.

---

## Requirements

### Requirement: Alertmanager webhook endpoint
The system SHALL expose `POST /api/v1/webhook/alertmanager` that accepts an Alertmanager-formatted JSON payload and returns HTTP 202 Accepted. The response body SHALL report, per alert in the payload, either the incident created for it or the reason it was rejected. It SHALL NOT return `signal_ids`: a bare `Signal` is no longer persisted independently of the incident it triggers.

#### Scenario: Valid payload is accepted
- **WHEN** a well-formed Alertmanager payload is posted to `/api/v1/webhook/alertmanager`
- **THEN** the response status is 202 and the body contains one entry per alert, each carrying its `signal_id` and either the resulting `incident_id`, target name and state, or a rejection reason

#### Scenario: Empty alerts list is accepted gracefully
- **WHEN** an Alertmanager payload with an empty `alerts` array is posted
- **THEN** the response status is 202, no incidents are created, and both the accepted and rejected lists are empty

---

### Requirement: Alertmanager payload normalization to Signal
The system SHALL normalize each alert in an Alertmanager payload to a canonical `Signal`. The normalizer SHALL be a standalone function in `yubarta/ingestion/normalizers/alertmanager.py`, not a method on `Signal`.

Required field mapping:
- `Signal.id` — deterministic from alert `fingerprint` + `startsAt`
- `Signal.fingerprint` — from alert `fingerprint`
- `Signal.status` — `firing` when alert `status == "firing"`, `resolved` when `status == "resolved"`
- `Signal.source` — always `webhook`
- `Signal.labels` — from alert `labels` dict
- `Signal.fired_at` — parsed from alert `startsAt`
- `Signal.raw` — the full original alert dict, unmodified

#### Scenario: Single firing alert is normalized
- **WHEN** an Alertmanager payload containing one firing alert is normalized
- **THEN** the result is a list with one `Signal` where `status == "firing"`, `source == "webhook"`, and `raw` contains the original alert dict

#### Scenario: Resolved alert sets correct status
- **WHEN** an Alertmanager payload with `status == "resolved"` on an alert is normalized
- **THEN** the resulting `Signal.status` is `"resolved"`

#### Scenario: Multiple alerts produce multiple Signals
- **WHEN** an Alertmanager payload contains three alerts
- **THEN** normalization returns a list of exactly three `Signal` objects

#### Scenario: Signal id is deterministic from fingerprint and startsAt
- **WHEN** the same alert is submitted twice
- **THEN** both produce a `Signal` with identical `id` values

---

### Requirement: Idempotent signal storage
The system SHALL create at most one `Incident` per distinct `Signal.id`. A second delivery of the same `Signal.id` SHALL be accepted (HTTP 202) and SHALL return the already-existing incident rather than creating a second one.

Idempotency SHALL be enforced by the unique constraint on `incidents.signal_id` in Postgres, not by a process-local structure. A restart, a second API replica, or a redelivery hours later therefore all deduplicate identically, which a per-process dictionary cannot do.

#### Scenario: First submission is stored
- **WHEN** a signal is received for the first time and resolves to exactly one target
- **THEN** an `Incident` is created in the `received` state and is retrievable by its incident id

#### Scenario: Duplicate submission is accepted but not stored twice
- **WHEN** the same `Signal.id` is submitted a second time
- **THEN** the response is 202, the returned `incident_id` is the one from the first submission, and exactly one incident row exists for that `signal_id`

#### Scenario: Deduplication survives a process restart
- **WHEN** the same `Signal.id` is submitted, the API process is restarted, and the same payload is submitted again
- **THEN** still exactly one incident exists for that `signal_id`

---

### Requirement: Storage dependency injection
The webhook route SHALL receive its `IncidentStore` implementation via FastAPI dependency injection (`Depends`). The route SHALL import only the `IncidentStore` Protocol from `yubarta/domain/ports.py`, never a concrete implementation.

#### Scenario: Store can be overridden in tests
- **WHEN** a test overrides the incident-store dependency
- **THEN** the route uses the test-supplied store, and the route module contains no import of `SqlAlchemyIncidentStore`

---

### Requirement: Target resolution happens at intake
The webhook route SHALL resolve each normalized `Signal` to exactly one `Target` using `target-inventory`'s matcher before creating an incident, and SHALL NOT create an incident for a signal that resolves to no target or to more than one.

An incident with no resolved target is not actionable by any later stage: the Director would have nothing to run a remediation against, and no credential to resolve. Rejecting at the boundary keeps that unactionable state out of the store entirely.

#### Scenario: Signal matching one target creates an incident for it
- **WHEN** an alert's labels match exactly one target in the inventory
- **THEN** an incident is created carrying that target's name

#### Scenario: Signal matching no target is rejected without creating an incident
- **WHEN** an alert's labels match no target in the inventory
- **THEN** no incident is created and the response reports that alert as rejected with a no-matching-target reason

#### Scenario: Signal matching several targets is rejected without creating an incident
- **WHEN** an alert's labels match more than one target in the inventory
- **THEN** no incident is created and the response reports that alert as rejected with an ambiguous-target reason naming the candidate targets

---

### Requirement: An unresolvable alert does not fail the whole delivery
The system SHALL return HTTP 202 for a well-formed payload even when some or all of its alerts are rejected, and SHALL process each alert independently so one rejected alert does not prevent incidents being created for the others.

A rejected alert is a well-formed request the system cannot act on, not a malformed one. Returning a non-2xx status would make Alertmanager retry the entire batch on a schedule, and a retry cannot fix missing inventory coverage, so it would loop until the inventory changes while also re-delivering the alerts that did succeed.

#### Scenario: Mixed payload creates incidents only for resolvable alerts
- **WHEN** a payload contains one alert matching a target and one matching nothing
- **THEN** the response is 202, one incident is created for the first alert, and the second is reported as rejected

#### Scenario: Fully unresolvable payload is still accepted
- **WHEN** every alert in a payload matches no target
- **THEN** the response is 202, the accepted list is empty, and every alert appears in the rejected list
