## Context

The `yubarta/ingestion/` module already exists with a stub route and commented-out prior work. The `Signal` type is canonical and defined in `yubarta/domain/signal.py`. The `SignalStore` Protocol is declared in `yubarta/domain/ports.py` with `add` and `get` methods. No concrete implementation exists yet. Postgres (stage 3) is the eventual store; this change uses an in-memory implementation.

The existing stub references Kafka, Redis, and a batch-threshold logic. All of that is out of scope for this stage.

**Deterministic boundary**: everything in this change is deterministic — no LLM is involved. The webhook handler normalizes and stores; that's it.

## Goals / Non-Goals

**Goals:**
- Accept Alertmanager webhook payloads at `POST /webhook/alertmanager`.
- Normalize the payload into a canonical `Signal` using a dedicated adapter.
- Store the signal via the `SignalStore` port using an in-memory adapter.
- Return idempotent 202 responses for duplicate signal ids without storing a duplicate.
- Integration test covering the full ingest path with a realistic Alertmanager payload.

**Non-Goals:**
- Persistent storage (Postgres — stage 3).
- Message bus publishing (Kafka — TBD).
- Batch/window logic, dedup-across-restarts, or any per-fingerprint counting.
- Routing to the remediation loop (stage 4).
- Any other webhook source (PagerDuty, Grafana, etc.).

## Decisions

### Decision: Alertmanager-specific normalizer as a standalone function, not a method on Signal

`Signal.from_alertmanager(payload)` couples the domain type to a specific source format. Instead, a `normalize_alertmanager(payload: dict) -> list[Signal]` function lives in `yubarta/ingestion/normalizers/alertmanager.py`. This keeps `Signal` source-agnostic and makes it trivial to add future sources without touching the domain type.

*Alternative considered*: classmethod on Signal. Rejected — violates the requirement that Signal carry no source-specific knowledge.

### Decision: One Signal per Alertmanager alert, not per group

Alertmanager batches alerts in a single webhook payload under `alerts[]`. Each alert in the list is normalized to its own `Signal`. This is the natural granularity for incident tracking — the remediation loop acts on individual conditions, not groups.

### Decision: In-memory SignalStore for now

A `yubarta/ingestion/store.py` module provides `InMemorySignalStore` — a dict keyed by `signal.id`. It satisfies the `SignalStore` Protocol. The route receives the store as a FastAPI dependency, making it easy to swap for a Postgres-backed implementation in stage 3 without changing the route logic.

*State guarantee*: in-memory only — no crash safety. Idempotency holds within a single process lifetime. This is acceptable for the learning milestone; noted as a known limitation.

### Decision: Route path is `/webhook/alertmanager`, separate from the existing `/ingest/` prefix

The existing `/api/v1/ingest/confluent` stub uses a capability-based path. Alertmanager's webhook target is conventionally `/webhook/<source>`. The route will live at `POST /api/v1/webhook/alertmanager` under a new `webhook` router in `yubarta/ingestion/`. The old stub (`/ingest/confluent`) is removed as dead code.

### Decision: Dependency injection for SignalStore via FastAPI `Depends`

The route receives a `SignalStore` instance via `Depends(get_signal_store)`. `get_signal_store` returns the singleton `InMemorySignalStore` in production. Tests override the dependency with a fresh instance per test. This avoids global state in tests and makes the seam explicit.

## Risks / Trade-offs

- **[Risk] Idempotency is process-scoped** → Mitigation: document clearly; Postgres store (stage 3) resolves this. For now, two restarts can re-process the same alert.
- **[Risk] Alertmanager payload schema changes** → Mitigation: normalizer accepts `dict` and extracts only the fields Signal needs; unknown fields are ignored. Tests use a realistic payload snapshot.
- **[Risk] InMemorySignalStore grows unbounded in long-running processes** → Mitigation: acceptable for the learning milestone; bounded by Postgres store in stage 3.

## Open Questions

- Should the `/ingest/confluent` stub be deleted entirely or left as a placeholder? *Decision: delete — it is dead code and the comment block already documents intent.*
