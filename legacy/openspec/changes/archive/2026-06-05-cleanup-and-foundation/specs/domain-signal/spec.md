## ADDED Requirements

### Requirement: Canonical Signal type
The system SHALL have a single canonical `Signal` type defined in `yubarta/domain/signal.py`. All capabilities that produce or consume an internal event SHALL use this type. No source-specific fields are permitted on `Signal` — those stay in the adapter that normalizes them.

Required fields:
- `id` — idempotency key, unique per event
- `fingerprint` — dedup key, stable across repeated firings of the same condition
- `status` — `firing` or `resolved`
- `source` — `webhook`, `scanner`, or `chatops`
- `labels` — arbitrary key-value pairs used for target matching
- `fired_at` — when the condition was detected
- `raw` — original payload preserved for diagnosis context

#### Scenario: Signal is source-agnostic
- **WHEN** a `Signal` is instantiated from a webhook payload
- **THEN** it contains no fields specific to the originating system (e.g. no `group_id`, `topic`, `lag`)

#### Scenario: Signal id is deterministic
- **WHEN** the same event is received twice with identical source fields
- **THEN** both produce a `Signal` with the same `id`

#### Scenario: Signal fingerprint is stable across firings
- **WHEN** the same condition fires repeatedly (e.g. disk above threshold multiple times)
- **THEN** each `Signal` for that condition has the same `fingerprint` regardless of `fired_at`

---

### Requirement: Signal status covers the full lifecycle
The `status` field SHALL support both `firing` and `resolved` values so that a self-recovery or external resolution can preempt an in-flight remediation loop.

#### Scenario: Resolved signal carries the same fingerprint as its firing signal
- **WHEN** a `resolved` Signal is created for a condition that previously fired
- **THEN** its `fingerprint` matches the original `firing` Signal's `fingerprint`

---

### Requirement: Raw payload preserved on Signal
The `raw` field SHALL store the original payload from the source adapter so the diagnosis agent can reason over unstructured evidence without the system re-fetching it.

#### Scenario: Raw field is populated on creation
- **WHEN** a Signal is created from any source
- **THEN** `signal.raw` contains the original payload dict and is not empty
