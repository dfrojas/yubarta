## 1. Domain model

- [x] 1.1 Create `yubarta/incident/__init__.py`
- [x] 1.2 Create `yubarta/incident/models.py` with `IncidentState` (`StrEnum`: `received`, `diagnosing`, `remediating`, `verifying`, `escalated`, `resolved`), `AttemptOutcome` (`StrEnum`: `succeeded`, `failed`, `skipped`), `AttemptApproval` (`StrEnum`: `not_required`, `pending`, `approved`, `denied`), `RemediationAttempt` (id, incident_id, remediation_name, idempotency_key, attempt_sequence, approval_status, approved_by, approved_at, started_at, completed_at, outcome, evidence), and `Incident` (id, signal, target_name, state, version, lease_owner, lease_generation, lease_expires_at, created_at, updated_at, attempts: list[RemediationAttempt])
- [x] 1.3 Add `IncidentTransition` (id, incident_id, from_state, to_state, occurred_at). Not in the original plan: the append-only log had no reader, which made "a restarted process folds the log to learn what happened" an untestable claim and left the table write-only

## 2. Postgres schema

- [x] 2.1 Add `alembic` to `pyproject.toml`, pinned `major.minor.patch`
- [x] 2.2 Run `alembic init` under `yubarta/infra/db/migrations/`; wire `env.py` to `settings.DATABASE_URI` and the SQLAlchemy metadata used by the new ORM tables
- [x] 2.3 In `yubarta/infra/db/orm.py`, remove the dead `alerts` table and commented-out `remediations` table
- [x] 2.4 In `yubarta/infra/db/orm.py`, define `incidents` (id, signal_id, signal_fingerprint, signal_raw JSONB, target_name, state, version, lease_owner nullable, lease_generation, lease_expires_at nullable, created_at, updated_at) with a unique constraint on `signal_id` and an index on `target_name`. `version` and `lease_generation` are non-null integers defaulting to 0; they are separate mechanisms and must not be collapsed into one counter
- [x] 2.5 In `yubarta/infra/db/orm.py`, define `incident_transitions` (id, incident_id FK, from_state, to_state, occurred_at) as append-only, indexed on `incident_id`
- [x] 2.6 In `yubarta/infra/db/orm.py`, define `remediation_attempts` (id, incident_id FK, remediation_name, idempotency_key unique, attempt_sequence, approval_status default `not_required`, approved_by nullable, approved_at nullable, started_at, completed_at, outcome nullable, evidence JSONB nullable), indexed on `incident_id` and unique on `idempotency_key`
- [x] 2.7 Regenerate the first Alembic revision from the schema in 2.3-2.6, replacing the existing revision rather than stacking a second one (nothing is deployed and no production data exists), and verify `alembic upgrade head` / `alembic downgrade base` both run cleanly against a local Postgres
  - Verified both directions, plus `alembic check` reporting no drift between the ORM and the revision (wired as `make migration-check`).
  - Discovered while verifying: editing a revision in place is invisible to a database that already ran it. The dev volume stayed on the old schema and the first `make inject-alarm` failed with `column "version" does not exist`, while the suite passed because integration tests create their database from scratch every run. `alembic downgrade base && alembic upgrade head` recovers it, and `dev-docs/dev.md` now says so.

## 3. Store port and repository

- [x] 3.1 In `yubarta/domain/ports.py`, replace `SignalStore` with an `IncidentStore` `Protocol`: `create`, `transition(incident_id, to_state, expected_version, lease_generation)`, `record_attempt`, `resolve_approval`, `complete_attempt`, `get`, `list_transitions`, `list_by_target`, `list_recent`
- [x] 3.2 Add `yubarta/infra/db/unit_of_work.py`: a Postgres-scoped Unit of Work per [ADR-0007](../../../records/adr/0007-postgres-scoped-unit-of-work.md) that owns the transaction boundary and commits or rolls back as one, so no store method calls `session.commit()` on its own. It SHALL NOT appear in the `IncidentStore` Protocol signature: the port stays free of SQLAlchemy
- [x] 3.3 In `yubarta/infra/db/repository.py`, replace the placeholder with `SqlAlchemyIncidentStore` implementing `IncidentStore`: `create` inserts `incidents` idempotently on `signal_id` conflict (returns the existing row instead of erroring)
- [x] 3.4 Implement `transition` as a conditional update guarded by `version` and `lease_generation`, inserting the `incident_transitions` row in the same transaction. Zero rows updated means rejected: re-read to distinguish a moved version (`ConcurrentModificationError`) from a superseded lease (`StaleLeaseError`), and `IncidentNotFoundError` if no row exists. No `SELECT ... FOR UPDATE`
  - The previous implementation used `.with_for_update()`, which ADR-0006 rejects by name. Removed.
  - The `from_state` for the log entry comes from a plain read before the update, not a lock. It is still correct whenever the update succeeds: any writer committing in between would have moved `version` and made the conditional update match no rows.
- [x] 3.5 Implement `record_attempt`: derive the idempotency key from `(incident_id, remediation_name, attempt_sequence)`, persist `approval_status` on the pre-execution row, insert before returning. Raise `DuplicateAttemptError` carrying the existing attempt so the caller can tell an in-flight attempt from a completed one. Never let the underlying integrity error escape the store
- [x] 3.6 Implement `resolve_approval`, `complete_attempt`, `get`, `list_transitions`, `list_by_target`, `list_recent` per the specs' read/write scenarios
- [x] 3.7 Update `yubarta/infra/db/initialization.py`: remove the no-op `create_database` stub and the commented-out `mapper_registry`/`start_mappers` references now that `orm.py` defines real tables directly
  - Resolves the design's open question about whether migrations run on app startup: **they do not**. `Database` builds an engine and nothing more. Migrations are a one-shot `migrate` compose service that the API waits on (`service_completed_successfully`), because the API is meant to run as several replicas and several of them racing to migrate one database on boot is worse than an ordered step.
  - Also deleted `yubarta/infra/db/sessions.py`: its `get_fastapi_session` read `app.state.db`, which nothing ever set, and it held a module-level `Database` instance built at import time.
- [x] 3.8 Define the store's error types as specific exception classes (`IncidentNotFoundError`, `AttemptNotFoundError`, `ConcurrentModificationError`, `StaleLeaseError`, `DuplicateAttemptError`, `IncidentStoreConsistencyError`), not generic exceptions

## 4. Intake wiring

- [x] 4.1 Add `yubarta/incident/dependencies.py` with a `get_incident_store` FastAPI dependency over the unit of work the lifespan builds
- [x] 4.2 Rewrite `yubarta/ingestion/routes/webhook.py`: normalize, resolve each `Signal` through the matcher, create an `Incident` per resolved signal, return 202 with per-alert accepted/rejected results. The route imports the `IncidentStore` Protocol only. `NoMatchingTargetError` and `AmbiguousTargetError` are caught per alert, not per request
- [x] 4.3 Delete `yubarta/ingestion/store.py` and the `get_signal_store` dependency
- [x] 4.4 Add `yubarta/incident/router.py` with `GET /api/v1/incidents/{incident_id}` (404 on unknown id, returning the incident plus its lifecycle log) and `GET /api/v1/incidents` (default bound, optional `target_name` filter), with Pydantic response models, and mount it in `yubarta/main.py`
- [x] 4.5 Verify `uvicorn yubarta.main:app` starts with no `ImportError`
  - Also added `yubarta/__init__.py`, `yubarta/incident/routes/__init__.py` and `yubarta/ingestion/routes/__init__.py`. The package was an implicit namespace package, which made mypy resolve the same file under two module names.
  - `main.py` now owns the engine in a lifespan context manager rather than at import time, per the project's FastAPI rule.
- [x] 4.6 Add `match_target_entry` to `yubarta/inventory/matcher.py`, returning the target's inventory name alongside the target. `match_target` keeps its exact signature and behaviour, so `target-inventory`'s requirements are unchanged. The store persists a name, and a `Target` instance means nothing outside the process that loaded the YAML

## 5. Tests

- [x] 5.1 Fix `tests/conftest.py`: it imported `start_mappers`, which does not exist, failing collection for the **entire** suite. Dropped it, replaced the deprecated session-scoped `event_loop` override with pytest-asyncio's loop-scope config, registered the `integration` marker, and made the database fixture opt-in so unit tests do not pay for a database they never touch
  - The test database's schema is now applied by the project's own Alembic migration instead of `metadata.create_all`, so a migration that drifts from the ORM fails the suite.
  - `pythonpath` in `pyproject.toml` pointed at `./src`, a directory that does not exist.
- [x] 5.2 Create `tests/integration/incident/test_store.py`: creation dedupes on `signal_id`; the full `received → diagnosing → remediating → verifying → resolved` sequence persists and reads back; the transition history folds back to the denormalized state; each transition increments `version`; a stale `expected_version` raises `ConcurrentModificationError` leaving state, version and the log untouched; a non-existent incident raises `IncidentNotFoundError`
  - Path deviation: under `tests/integration/incident/` rather than `tests/incident/`, to match the repository's existing `unit/` vs `integration/` split.
- [x] 5.3 Extend it: an attempt is recorded before completion and readable with no outcome; completing it updates outcome and timestamp; a repeated idempotency key raises `DuplicateAttemptError` carrying the existing attempt, both in flight and completed; a `pending` attempt resolves to `approved`/`denied` with approver and timestamp, and a non-approval attempt stays `not_required`
- [x] 5.4 Add tests for `list_by_target` (only matching target, most-recent-first) and `list_recent` (bounded to N, most-recent-first)
- [x] 5.5 Add fencing tests: a stale `lease_generation` raises `StaleLeaseError` **even when `expected_version` matches**, and the current generation is accepted
- [x] 5.6 Add a Unit of Work rollback test: a failure partway through a transition leaves neither the state update nor the transition row committed
- [x] 5.7 Rewrite `tests/integration/ingestion/test_webhook.py` against the incident flow: a matching alert creates one `received` incident; a redelivery returns the same id and creates no second row; alerts matching no target or several are rejected with no incident created; a mixed payload creates incidents only for the resolvable alerts
- [x] 5.8 Add `tests/integration/incident/test_routes.py`: a known incident returns its state, attempts and lifecycle log, an unknown id returns 404, the list read is bounded by default, rejects an out-of-range limit, and filters by `target_name`
- [x] 5.9 Cover the three delta-spec scenarios the first pass missed, found while verifying: deduplication does not depend on process-local state (a second `TestClient` runs the lifespan again, so it has its own engine and carries nothing over in memory), a payload where *every* alert is unresolvable is still accepted, and the route module references neither `SqlAlchemyIncidentStore` nor SQLAlchemy at all (a static check, since what is being protected is an import rather than a behaviour)
- [x] 5.10 66 tests pass. `ruff check` and `mypy .` (strict) are clean, both of which were failing before this change: `mypy` could not even resolve modules, and `ruff` reported 11 errors, so CI was red on `main`

## 6. Dev environment

- [x] 6.1 Remove the `rust-director` stage from the `Dockerfile` and the `director` service from `docker-compose.dev.yaml`. Both built from `yubarta/director/Cargo.toml` and `yubarta/director/src/`, deleted by `cleanup-and-foundation`, so `docker compose build` failed before any service started. Also deleted `bin/wait-for-it.sh`, whose only caller was that compose file
- [x] 6.2 Give `postgres`, `kafka` and `redis` healthchecks. `api` waits on Postgres being healthy and the migration having completed, and deliberately does **not** wait on Kafka or Redis: no code path reaches them, so gating on them would slow every `compose run`
  - Dropped the host port publications for Kafka and Redis. Redis collided with another container already on 6379, and Kafka's advertised listener is `kafka:9092`, so a host client is handed an address it cannot resolve regardless.
  - The `Dockerfile` now copies the project into the image (it was commented out), so it no longer depends on the bind mount to have any code.
- [x] 6.3 Add the Makefile targets the workflow references: `test` (`CLAUDE.md` documents `make test` but only `run-tests` existed), plus `up`, `down`, `clean`, `logs`, `check`, `psql`, `shell`, `incidents`, `migration-check` and `inject-alarm`. Lint and type checks run with `--no-deps` so they do not raise a database
- [x] 6.4 Add `dev/inject_alarm.py`: posts a fake Alertmanager payload matching `java-app-1` in `inventory.yaml`, reads the resulting incident back through the API, redelivers to show deduplication, and posts an unmatchable alert to show the rejection path
- [x] 6.5 Write `dev-docs/dev.md`, referenced from `CLAUDE.md` but missing
- [x] 6.6 Confirm the rig's Postgres service and `.env` DB settings are sufficient for the new schema. They are. Filled in the empty `.env.example` and added `DB_ECHO`
- [x] 6.7 Verified against the raised stack: `make up` (migration runs, API healthy), `make test` (62 passed), `make check` (clean), `make inject-alarm` (incident created, read back, deduplicated on redelivery, unmatched alert rejected), and the row confirmed directly with `psql`

## 7. Learning Note

- [x] 7.1 Write `dev-docs/learnings/incident-store.md` covering: the append-only-transitions-plus-denormalized-state design, the three-mechanism concurrency model (optimistic `version`, `lease_generation` fencing token, pre-execution idempotency key) and the distinct race each one solves, why the design reversed from pessimistic row locking, why the Unit of Work pattern was introduced at all given nothing in the project used one before this stage (transaction boundary as an explicit domain concept rather than an emergent property of session lifetime or code layout, keeping SQLAlchemy out of the port) and what was rejected on the way there (per-repository-method commits, caller-supplied sessions), and anything surprising discovered during implementation
- [x] 7.2 Update `dev-docs/roadmap.md`: stage 3 status, and note that a stage is only "done" once its driver script runs against the raised stack, which is the check that would have caught the rig having been broken since stage 0
