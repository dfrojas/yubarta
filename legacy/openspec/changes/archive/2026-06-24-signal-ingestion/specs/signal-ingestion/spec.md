## ADDED Requirements

### Requirement: Alertmanager webhook endpoint
The system SHALL expose `POST /api/v1/webhook/alertmanager` that accepts an Alertmanager-formatted JSON payload and returns HTTP 202 Accepted.

#### Scenario: Valid payload is accepted
- **WHEN** a well-formed Alertmanager payload is posted to `/api/v1/webhook/alertmanager`
- **THEN** the response status is 202 and the body contains `signal_ids` with one entry per alert in the payload

#### Scenario: Empty alerts list is accepted gracefully
- **WHEN** an Alertmanager payload with an empty `alerts` array is posted
- **THEN** the response status is 202 and `signal_ids` is an empty list

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
The system SHALL store each `Signal` exactly once, keyed by `signal.id`. A second write with the same id SHALL be accepted (HTTP 202) but SHALL NOT create a duplicate entry.

#### Scenario: First submission is stored
- **WHEN** a signal is received for the first time
- **THEN** it is retrievable from the store by its id

#### Scenario: Duplicate submission is accepted but not stored twice
- **WHEN** the same signal id is submitted a second time
- **THEN** the response is 202 and the store contains exactly one entry for that id

---

### Requirement: SignalStore dependency injection
The webhook route SHALL receive its `SignalStore` implementation via FastAPI dependency injection (`Depends`). The route SHALL import only the `SignalStore` Protocol, not a concrete implementation.

#### Scenario: Store can be overridden in tests
- **WHEN** a test overrides the `get_signal_store` dependency with a fresh `InMemorySignalStore`
- **THEN** the route uses the test-supplied store with no shared state between tests

---

### Requirement: In-memory SignalStore implementation
The system SHALL provide `InMemorySignalStore` in `yubarta/ingestion/store.py` that satisfies the `SignalStore` Protocol. It SHALL store signals in a dict keyed by `signal.id`.

#### Scenario: add returns the stored Signal
- **WHEN** `InMemorySignalStore.add(signal)` is called
- **THEN** it returns the same signal and the signal is retrievable via `get(signal.id)`

#### Scenario: get returns None for unknown id
- **WHEN** `InMemorySignalStore.get("nonexistent-id")` is called
- **THEN** it returns `None`
