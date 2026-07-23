## Why

Target capability: `incident-store`.

The remediation loop (stage 4) is an explicit, checkpointed state machine (`Received → Diagnosing → Remediating → Verifying → retry | Escalated | Resolved`); it cannot be built without somewhere durable to persist that state. Without a store, a crashed run has no way to resume instead of restarting, and re-running a destructive remediation on restart is the exact failure the spec calls out to avoid. Incident history also feeds downstream capabilities directly: ChatOps deterministic reads ("which remediation fixed the last crash?"), the eval harness that replays recorded incidents, and (indirectly, via a future indexing step into a still-undecided vector store) the diagnosis agent's RAG layer. Building the store now, ahead of the orchestrator, lets stage 4 be pure state-machine logic against an already-proven persistence contract.

## What Changes

- Add an `Incident` domain model: one incident per Signal-driven remediation attempt, carrying its current lifecycle state, the originating Signal, the resolved Target, and an ordered history of remediation attempts.
- Add a `RemediationAttempt` model: one row per remediation execution, recording the remediation name, an idempotency key recorded **before** execution (not after), start/end timestamps, and outcome (`succeeded`, `failed`, `skipped`).
- Define the lifecycle states as a closed enum: `received`, `diagnosing`, `remediating`, `verifying`, `escalated`, `resolved`. (The spec's `retry` is not a state — it's a transition back to `diagnosing` or `remediating` after a failed `verifying`.)
- Add a Postgres schema (SQLAlchemy 2.0 Core/ORM) for `incidents` and `remediation_attempts`, replacing the dead `alerts` table and commented-out `remediations` table in `yubarta/infra/db/orm.py`.
- Add an `IncidentStore` port (`Protocol`) in `yubarta/domain/ports.py` and a `SqlAlchemyIncidentStore` implementation in `yubarta/infra/db/repository.py`, replacing the current placeholder `SqlAlchemySignalRepository`.
- Store operations: create an incident from a Signal + matched Target, append a state transition (with the new state persisted atomically with any attempt it produced), append a remediation attempt (idempotency key written before execution), and read incident history (by id, by target, most-recent-N) for ChatOps/RAG/eval consumers.
- Introduce Alembic for migrations. There is currently no migration tooling in the project (`Database.create_database` is a no-op stub); one is needed before a real schema exists, since ad-hoc `create_all` calls don't handle production upgrades safely.
- **BREAKING**: removes the dead `alerts` table and the unused `SignalStore` port (superseded by `IncidentStore`, since signals themselves are not independently persisted, only as the trigger embedded in an Incident). Both are pre-existing, unused scaffolding from before the `Signal` model existed, so nothing currently depends on them.

## Capabilities

### New Capabilities
- `incident-store`: Postgres-backed persistence for incident lifecycle state and remediation outcomes, exposed as a domain port for the orchestrator (stage 4), ChatOps (stage 10), and the eval harness (stage 12) to build on directly. The diagnosis agent's RAG layer (stage 8) will consume this data indirectly, via whatever indexing step feeds its still-undecided vector store, not by querying this port as its retrieval source.

### Modified Capabilities
(none — `signal-ingestion` and `target-inventory` are consumed as inputs, not modified)

## Impact

- **New**: `yubarta/incident/` (domain model, lifecycle enum), Alembic config + first migration, `IncidentStore` port, `SqlAlchemyIncidentStore` repository, tests under `tests/incident/`.
- **Modified**: `yubarta/infra/db/orm.py` (drop `alerts`/commented `remediations`, add `incidents`/`remediation_attempts` tables), `yubarta/infra/db/initialization.py` (`create_database` becomes a real Alembic-driven or metadata-driven bootstrap), `yubarta/infra/db/repository.py` (replace placeholder), `yubarta/domain/ports.py` (replace `SignalStore` with `IncidentStore`).
- **Dependencies**: adds `alembic` to `pyproject.toml`, pinned to a full `major.minor.patch`.
- **Not in scope**: the orchestrator/state machine driver itself (stage 4, `remediation-loop`), ChatOps read endpoints (stage 10), RAG indexing of incident history (stage 8). This change only makes the state durable and queryable; it does not decide when transitions happen.
