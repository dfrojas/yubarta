# Capability: Incident Store

## Purpose

Postgres-backed persistence for an incident's lifecycle state and its remediation
outcomes, exposed as a domain port (`IncidentStore`) rather than as a database.

One incident is one Signal-driven remediation lifecycle: the triggering `Signal`, the
target it resolved to, the current state, the append-only log of every state change, and
every remediation attempt with its approval trail and outcome.

The store never decides when a transition happens. It makes the state durable, readable,
and safe to write concurrently, so the orchestrator (`remediation-loop`), ChatOps
(`chatops-interface`) and the eval harness (`evaluation-harness`) all build on one
persistence contract, and none of them touches SQLAlchemy.

Concurrency safety rests on three deliberately separate mechanisms, one per race
([ADR-0006](../../../records/adr/0006-three-mechanism-concurrency-model.md)): an
optimistic `version` for lost updates, a `lease_generation` fencing token for a
superseded owner, and a pre-execution idempotency key for duplicate external effects.
Atomic database writes are bounded by a Postgres-scoped Unit of Work
([ADR-0007](../../../records/adr/0007-postgres-scoped-unit-of-work.md)).

---

## Requirements

### Requirement: Incident creation from a matched Signal and Target
The system SHALL create exactly one `Incident` per distinct `Signal.id`, in the `received` state, persisting the triggering `Signal` and the resolved target's name. Deduplication is unconditional and does not depend on the incident's state: a genuine recurrence of the same condition already carries a different `Signal.id` (ADR-0004, `fingerprint + fired_at`), so a repeated `Signal.id` is always a redelivery, never a new occurrence.

#### Scenario: New signal creates a new incident
- **WHEN** a `Signal` with a `Signal.id` not already persisted is matched to a `Target`
- **THEN** the store creates a new `Incident` in the `received` state referencing that `Signal` and target name

#### Scenario: Duplicate signal does not create a duplicate incident
- **WHEN** a `Signal` with the same `Signal.id` as an already-persisted incident is submitted again
- **THEN** the store does not create a second `Incident` for it

---

### Requirement: Incident lifecycle transitions are persisted atomically
The system SHALL persist every incident state transition as an append-only record, and SHALL update the incident's current-state field in the same transaction as that record, so the two can never disagree.

#### Scenario: Valid transition is recorded
- **WHEN** an incident in state `diagnosing` transitions to `remediating`
- **THEN** the store appends a transition record `diagnosing → remediating` and updates the incident's current state to `remediating`, both durably committed together

#### Scenario: Transition history reconstructs current state
- **WHEN** an incident's full transition history is read back
- **THEN** folding the transitions in order yields the same state as the incident's denormalized current-state field

#### Scenario: A failure inside the transaction leaves neither write
- **WHEN** a transition fails partway through, after the state update and the transition record but before the commit
- **THEN** neither is persisted, and the incident's state, version and transition log are unchanged

---

### Requirement: State transitions are guarded by an expected version
The system SHALL require an expected version on every incident state transition, SHALL increment the incident's version on a successful transition, and SHALL reject a transition whose expected version does not match the persisted version rather than applying it.

#### Scenario: Successful transition increments the version
- **WHEN** an incident at version 7 transitions from `diagnosing` to `remediating` with expected version 7
- **THEN** the transition is applied and the incident's version becomes 8

#### Scenario: Stale expected version is rejected
- **WHEN** two writers both read an incident at version 7, the first writer's transition commits, and the second writer then submits its transition with expected version 7
- **THEN** the store rejects the second as a concurrent-modification error, leaves the incident's state and version unchanged, and appends no transition record

---

### Requirement: Writes from a superseded lease are rejected
The system SHALL record a lease generation on each incident and SHALL reject any state-changing write carrying a lease generation older than the persisted one, independently of whether that write's expected version matches.

#### Scenario: A stale owner is rejected even with a correct expected version
- **WHEN** a writer submits a transition whose expected version matches the incident's persisted version but whose lease generation is older than the incident's persisted lease generation
- **THEN** the store rejects it as a stale-lease error and applies nothing

#### Scenario: The current owner's write is accepted
- **WHEN** a writer submits a transition whose expected version and lease generation both match the persisted values
- **THEN** the transition is applied and recorded

---

### Requirement: Remediation attempts are recorded before execution
The system SHALL persist a `RemediationAttempt` record, including its idempotency key, before the remediation it describes is executed, and SHALL update that same record with the outcome once execution completes. This mechanism is independent of the version guard and the lease fencing token: it prevents duplicate execution of an external effect, which neither of those can prevent, and they in turn prevent lost updates and stale ownership, which it cannot.

#### Scenario: Attempt is recorded pre-execution
- **WHEN** the orchestrator decides to run a remediation for an incident
- **THEN** the store persists a `RemediationAttempt` row with a deterministic idempotency key derived from the incident id, remediation name, and attempt sequence, before the remediation runs

#### Scenario: Idempotency key detects a repeated attempt after a crash
- **WHEN** a `RemediationAttempt` is looked up by its deterministic idempotency key and a matching row already exists with no recorded outcome
- **THEN** the caller can determine the remediation may already be in flight or have run, instead of blindly re-executing it

#### Scenario: A completed attempt is not re-executed
- **WHEN** a `RemediationAttempt` is recorded whose deterministic idempotency key already belongs to an attempt with a recorded outcome
- **THEN** the store rejects the write and surfaces the existing attempt, including its outcome, so the caller can read the result instead of executing the remediation again

#### Scenario: Attempt outcome is recorded after execution
- **WHEN** a previously recorded `RemediationAttempt` completes
- **THEN** the store updates that same row with its outcome (`succeeded`, `failed`, or `skipped`) and completion timestamp

---

### Requirement: Per-attempt approval is auditable
The system SHALL record the approval status of each `RemediationAttempt` (`not_required`, `pending`, `approved`, `denied`) together with who approved it and when, so an approval-requiring execution has a durable audit trail. The system SHALL NOT store whether a remediation *requires* approval — that is a static property of the remediation definition, owned by the remediation registry.

#### Scenario: An attempt that requires no approval
- **WHEN** a `RemediationAttempt` is recorded for a remediation that requires no approval
- **THEN** its approval status is `not_required` and no approver is recorded

#### Scenario: An approval-requiring attempt is recorded pending before execution
- **WHEN** a `RemediationAttempt` is recorded for a remediation that requires approval
- **THEN** the store persists it with approval status `pending` before the remediation runs, and the approval decision (`approved` or `denied`, with the approver's identity and timestamp) can be recorded against that same row once it is made, independent of the channel the approval arrived through

---

### Requirement: Incident history is readable by id, by target, and as a recent list
The system SHALL expose read operations for a single incident by id, all incidents for a given target name, the most recent N incidents, and an incident's transition log, each including their remediation attempts.

The transition log is readable and not only appendable: crash recovery folds it to learn what actually happened, so a write-only log would make that guarantee unverifiable.

#### Scenario: Read by id includes attempts
- **WHEN** an incident is read by its id
- **THEN** the result includes the incident's current state, its triggering signal, and the ordered list of its remediation attempts

#### Scenario: Read by target name returns only that target's incidents
- **WHEN** incidents are read for a given target name
- **THEN** the result includes only incidents whose `target_name` matches, ordered most-recent-first

#### Scenario: Recent incidents are bounded
- **WHEN** the most recent N incidents are requested
- **THEN** the result contains at most N incidents, ordered most-recent-first, regardless of total incident count in the store

#### Scenario: Transition log is readable in order
- **WHEN** an incident's transition log is read
- **THEN** the result contains every state change in the order it occurred, each with its origin state, destination state and timestamp

---

### Requirement: Incident history is readable over HTTP

The system SHALL expose `GET /api/v1/incidents/{incident_id}` and `GET /api/v1/incidents` (bounded, optionally filtered by target name), both served through the `IncidentStore` port.

These exist so persisted state is observable before a Director exists: without them, the only evidence an incident was stored is a direct database query, which no consumer of this capability would ever do. They are deterministic reads in the sense stage 10 uses the term (no LLM in the path), and ChatOps will consume the same port rather than reimplementing the queries.

#### Scenario: Reading a known incident returns its full history
- **WHEN** `GET /api/v1/incidents/{incident_id}` is called for an existing incident
- **THEN** the response is 200 with the incident's state, version, triggering signal, target name, ordered remediation attempts, and its transition log

#### Scenario: Reading an unknown incident is a 404
- **WHEN** `GET /api/v1/incidents/{incident_id}` is called with an id that does not exist
- **THEN** the response is 404 with a message naming the missing id, not a 500 and not an empty 200

#### Scenario: The list read is bounded by default
- **WHEN** `GET /api/v1/incidents` is called with no limit
- **THEN** it applies a default bound rather than returning every incident ever stored

#### Scenario: The list read can be filtered by target
- **WHEN** `GET /api/v1/incidents?target_name=java-app-1` is called
- **THEN** the response contains only incidents for that target, most-recent-first

---

### Requirement: Schema changes ship as migrations
The system SHALL manage its schema with Alembic migrations, and SHALL NOT apply them from the application's startup path.

Startup migration is rejected because the API is intended to run as more than one replica, and several replicas racing to migrate one database on boot is a worse failure mode than a deploy step that has to be ordered.

#### Scenario: Migrations run as an explicit step
- **WHEN** the dev rig is raised
- **THEN** `alembic upgrade head` runs as a one-shot step that the API waits for, and the API's own startup performs no schema work

#### Scenario: Schema and ORM definitions agree
- **WHEN** the migration history is compared against the ORM table definitions
- **THEN** no pending schema difference is reported
