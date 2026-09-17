# 6. Three-mechanism concurrency model

Date: 2026-07-23

## Status

Accepted

Built on by [7. Postgres-scoped Unit of Work](0007-postgres-scoped-unit-of-work.md)

## Context

The Director, the deterministic orchestrator that drives an incident through its lifecycle, deploys as multiple concurrent replicas consuming from Kafka. "One Director per incident" is therefore not structurally guaranteed: a consumer-group rebalance or a lapsed ownership lease can briefly put two replicas on the same incident. Reducing that overlap to rare belongs to the Director; staying correct when it happens anyway belongs to the persistence layer.

Three distinct races can occur, and they are easy to mistake for one:

1. **Lost update.** Two writers read the same incident state, both decide, both write, and the second silently overwrites the first.
2. **Stale owner.** A replica whose lease has expired continues acting as the authoritative owner after another replica has taken over. It can hold a perfectly consistent view of the persisted state and still have no right to act.
3. **Duplicate external effect.** The same remediation, an SSH command or an API call, executes twice.

The `incident-store` design initially chose pessimistic row locking (`SELECT ... FOR UPDATE`) for the first race and explicitly rejected a version column. That was wrong for a state machine driven by a possibly-stale replica: pessimistic locking makes the second writer *wait* and then succeed, which means a decision computed from pre-lock state still gets applied. The conflict is not lock contention to be smoothed over, it is evidence that the caller's view is stale.

Options rejected: collapsing the version counter and the fencing token into a single number (loses one of the two guarantees, since a consistent version says nothing about ownership); treating the idempotency key as sufficient on its own (it protects external effects, not persisted state); relying on the Director to check its own lease validity (a stale replica does not know it is stale, so a self-check is worthless by construction).

## Decision

Three separate mechanisms, one per race, never combined.

**`version`, optimistic concurrency control over persisted execution state.** State transitions are conditional updates carrying an expected version. A successful transition increments it. A mismatch is a concurrent modification and is surfaced explicitly to the caller rather than applied; the caller re-reads and re-decides. This replaces pessimistic row locking.

**`lease_generation`, a fencing token.** A monotonic counter identifying successive acquisitions of an ownership lease, incremented by the Director on each acquisition. Every state-changing write carries the caller's generation and is rejected if it is older than the persisted one, independently of whether its expected version matches. Enforcement lives in the store, at the resource, because a fencing token that only the client checks is not a fencing token.

**Idempotency key, recorded before execution.** A deterministic key written and committed before a remediation runs, under a unique constraint. It prevents duplicate execution of external effects. It is not a substitute for optimistic concurrency control or lease ownership, and neither of those substitutes for it.

Postgres stores durable state and coordinates database-level concurrency. Kafka is the messaging and work-distribution mechanism; Postgres is not the queue.

## Consequences

### Positive

- Each race has one mechanism responsible for it, so a future reader can tell which guarantee a given column or constraint carries.
- Conflicts surface as explicit, distinguishable errors rather than silently-applied stale decisions.
- The store stays correct under multi-replica execution without assuming a single writer.

### Negative

- Callers must handle rejection, re-read and re-decide, rather than blindly retrying. A blind retry re-applies a decision made from stale state, which is exactly the failure pessimistic locking would have hidden.
- Three mechanisms are more surface than one, and the temptation to merge the version counter and the fencing token will recur. Merging them silently removes one guarantee without any test failing unless that case is covered explicitly.
- `lease_generation` is enforced from the `incident-store` stage but nothing increments it until the Director stage exists, so the fencing predicate always passes in the interim.

### Mitigations

- An integration test asserts that a stale `lease_generation` is rejected *even when the expected version matches*, which is what keeps the two mechanisms from collapsing into one during implementation.
- Lease TTL and heartbeat interval are deliberately left to the Director stage, which is what acquires leases; the store only enforces the token.
