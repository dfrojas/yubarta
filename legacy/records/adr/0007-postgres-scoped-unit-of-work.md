# 7. Postgres-scoped Unit of Work

Date: 2026-07-23

## Status

Accepted

Builds on [6. Three-mechanism concurrency model](0006-three-mechanism-concurrency-model.md)

## Context

Until the `incident-store` stage, nothing in this project needed a transaction boundary: there was no real schema. The incident store changes that, because its guarantees are multi-write. Persisting a state transition means a conditional `UPDATE` on the incident row plus an `INSERT` into the append-only transition log, and the claim that the denormalized current state can never drift from the log rests entirely on those two landing together or not at all.

Left implicit, that boundary belongs to whoever happens to hold the database session. Two ways that fails:

- **Per-repository-method commits.** Each store method commits on its own, so the state update can commit while the transition insert fails. The atomicity guarantee is gone, and nothing in the code says it was ever intended.
- **Caller-supplied sessions.** The orchestrator opens and commits the session. This works, but it pushes SQLAlchemy into the Director, which is precisely what the domain port exists to prevent.

There is a second reason to name the boundary rather than leave it emergent. Remediations perform external effects (SSH, HTTP, infrastructure APIs) that cannot enlist in a Postgres transaction and cannot be undone by a rollback. Whether those effects sit inside or outside the atomic region should be a stated decision, not a consequence of where someone happened to put a `with` block.

## Decision

Introduce a Unit of Work that coordinates atomic database changes, scoped to PostgreSQL operations only.

The Unit of Work owns the transaction boundary: the conditional state update, its transition record, and attempt writes commit or roll back together. "What commits together" is a decision the store states, not an emergent property of session lifetime or code layout, and it is expressed without leaking the ORM through the domain port.

External SSH, TCP, HTTP, and infrastructure actions never execute inside a unit of work. Record-before-execute is the compensating pattern: the attempt row, with its idempotency key, commits before the effect runs; the outcome commits after. A crash between the two is therefore detectable on restart rather than silent.

## Consequences

### Positive

- Atomicity guarantees are stated and enforced in one place instead of being reconstructed by reading every repository method.
- Consumers of the store (the Director, ChatOps, the eval harness) never touch SQLAlchemy sessions.
- The atomic region stays small and explicit, which makes it visible that external effects sit between units of work rather than inside one.

### Negative

- More indirection than calling the session directly, and one more concept to learn before writing a store method.
- The boundary is only as good as its use: a method that quietly opens its own session bypasses it, and nothing structural prevents that.
- Compensation for failed external effects is left to the caller. A rollback cannot undo an SSH command, so partial-failure handling moves into the Director rather than disappearing.

### Mitigations

- The record-before-execute ordering, backed by the idempotency key from [6. Three-mechanism concurrency model](0006-three-mechanism-concurrency-model.md), makes an interrupted external effect detectable rather than requiring it to be undone.
