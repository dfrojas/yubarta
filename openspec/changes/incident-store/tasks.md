## 1. Domain model

- [x] 1.1 Create `yubarta/incident/__init__.py`
- [x] 1.2 Create `yubarta/incident/models.py` with `IncidentState` (`StrEnum`: `received`, `diagnosing`, `remediating`, `verifying`, `escalated`, `resolved`), `AttemptOutcome` (`StrEnum`: `succeeded`, `failed`, `skipped`), `AttemptApproval` (`StrEnum`: `not_required`, `pending`, `approved`, `denied`), `RemediationAttempt` (id, incident_id, remediation_name, idempotency_key, attempt_sequence, approval_status, approved_by, approved_at, started_at, completed_at, outcome, evidence), and `Incident` (id, signal, target_name, state, created_at, updated_at, attempts: list[RemediationAttempt])

## 2. Postgres schema

- [x] 2.1 Add `alembic` to `pyproject.toml`, pinned `major.minor.patch`
- [x] 2.2 Run `alembic init` under `yubarta/infra/db/migrations/`; wire `env.py` to `settings.DATABASE_URI` and the SQLAlchemy metadata used by the new ORM tables
- [x] 2.3 In `yubarta/infra/db/orm.py`, remove the dead `alerts` table and commented-out `remediations` table
- [x] 2.4 In `yubarta/infra/db/orm.py`, define `incidents` (id, signal_id, signal_fingerprint, signal_raw JSONB, target_name, state, created_at, updated_at) with a unique constraint on `signal_id` and an index on `target_name`
- [x] 2.5 In `yubarta/infra/db/orm.py`, define `incident_transitions` (id, incident_id FK, from_state, to_state, occurred_at) as append-only, indexed on `incident_id`
- [x] 2.6 In `yubarta/infra/db/orm.py`, define `remediation_attempts` (id, incident_id FK, remediation_name, idempotency_key unique, attempt_sequence, approval_status default `not_required`, approved_by nullable, approved_at nullable, started_at, completed_at, outcome nullable, evidence JSONB nullable), indexed on `incident_id` and unique on `idempotency_key`
- [x] 2.7 Generate the first Alembic revision from the schema in 2.3-2.6 and verify `alembic upgrade head` / `alembic downgrade base` both run cleanly against a local Postgres

## 3. Store port and repository

- [ ] 3.1 In `yubarta/domain/ports.py`, replace `SignalStore` with an `IncidentStore` `Protocol`: `create(signal: Signal, target_name: str) -> Incident`, `transition(incident_id: str, to_state: IncidentState) -> Incident`, `record_attempt(incident_id: str, remediation_name: str, approval_status: AttemptApproval = AttemptApproval.not_required) -> RemediationAttempt`, `resolve_approval(attempt_id: str, approval_status: AttemptApproval, approved_by: str | None) -> RemediationAttempt`, `complete_attempt(attempt_id: str, outcome: AttemptOutcome, evidence: dict | None) -> RemediationAttempt`, `get(incident_id: str) -> Incident | None`, `list_by_target(target_name: str) -> list[Incident]`, `list_recent(limit: int) -> list[Incident]`
- [ ] 3.2 In `yubarta/infra/db/repository.py`, replace the placeholder `SqlAlchemySignalRepository` with `SqlAlchemyIncidentStore` implementing `IncidentStore`: `create` inserts `incidents` idempotently on `signal_id` conflict (returns the existing row instead of erroring)
- [ ] 3.3 Implement `transition`: within one transaction, `SELECT ... FOR UPDATE` the incident row, insert into `incident_transitions` (from current state to `to_state`), update `incidents.state`; the row lock serializes concurrent transitions so neither is lost. Raise a specific `IncidentNotFoundError` if the incident does not exist
- [ ] 3.4 Implement `record_attempt`: derive the idempotency key from `(incident_id, remediation_name, attempt_sequence)`, persist `approval_status` (default `not_required`) on the pre-execution row, insert before returning; raise a specific `DuplicateAttemptError` if the idempotency key already exists with no outcome recorded
- [ ] 3.5 Implement `resolve_approval` (set `approval_status` to `approved`/`denied` with `approved_by`/`approved_at` on the recorded row), `complete_attempt`, `get`, `list_by_target`, `list_recent` per the specs' read/write scenarios
- [ ] 3.6 Update `yubarta/infra/db/initialization.py`: replace the no-op `create_database` stub with an `alembic upgrade head` invocation (or a documented equivalent), removing the commented-out `mapper_registry`/`start_mappers` references now that `orm.py` defines real tables directly

## 4. Tests

- [ ] 4.1 Create `tests/incident/test_store.py` (integration, real Postgres per the project's testing rule): incident creation dedupes on `signal_id`; a full `received → diagnosing → remediating → verifying → resolved` transition sequence persists correctly and is readable back; the transition history folds back to the denormalized current state; transitioning a non-existent incident raises `IncidentNotFoundError`
- [ ] 4.2 Extend `tests/incident/test_store.py`: an attempt is recorded before completion and readable with no outcome; completing it updates outcome and timestamp; a repeated idempotency key with no outcome raises `DuplicateAttemptError`; an attempt recorded `pending` resolves to `approved`/`denied` via `resolve_approval` with approver and timestamp, and a non-approval attempt stays `not_required`
- [ ] 4.3 Add tests for `list_by_target` (only matching target, most-recent-first) and `list_recent` (bounded to N, most-recent-first)

## 5. Dev environment

- [ ] 5.1 Document the `alembic upgrade head` step in `dev-docs/dev.md`'s local setup instructions
- [ ] 5.2 Confirm the dev rig's docker-compose Postgres service and `.env` DB settings are sufficient for the new schema (no changes expected, verify only)

## 6. Learning Note

- [ ] 6.1 Write `dev-docs/learnings/incident-store.md` covering: the append-only-transitions-plus-denormalized-state design, the idempotency-key-before-execution decision, and anything surprising discovered during implementation
