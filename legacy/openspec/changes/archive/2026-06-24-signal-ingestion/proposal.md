## Why

The system has a canonical `Signal` type and a clean project structure, but no path to get external alerts into the system. Without ingestion, nothing can trigger the remediation loop. This change wires the first entry point: Alertmanager webhooks received, normalized, and stored idempotently.

## What Changes

- New FastAPI route `POST /webhook/alertmanager` under `yubarta/ingestion/` that accepts Alertmanager's `application/json` payload.
- Alertmanager-specific normalization adapter that maps the payload to the canonical `Signal` type.
- Idempotent write: signals with the same `id` are accepted without error but not duplicated.
- In-memory `SignalStore` implementation (satisfies the `SignalStore` Protocol from `domain/ports.py`) — Postgres store is deferred to stage 3 (`incident-store`).
- Integration test using a real Alertmanager-shaped payload that verifies normalization and idempotency end-to-end.

## Capabilities

### New Capabilities

- `signal-ingestion`: Alertmanager webhook receiver that normalizes incoming alerts to `Signal` and stores them via the `SignalStore` port.

### Modified Capabilities

*(none — no existing spec-level behavior changes)*

## Impact

- **New module**: `yubarta/ingestion/` — route, normalizer, in-memory store adapter.
- **`yubarta/main.py`**: registers the ingestion router.
- **`yubarta/domain/ports.py`**: `SignalStore` Protocol is already declared; this change provides its first concrete implementation.
- **No breaking changes** to existing specs (`domain-signal`, `project-structure`).
- **Deferred**: persistent Postgres store (stage 3), queue layer (TBD), dedup across restarts (requires Postgres).

## Non-goals

- Persistent storage across restarts (stage 3).
- Proactive scanner signals (stage 6).
- Routing signals to the remediation loop (stage 4).
- Any LLM involvement — ingestion is fully deterministic.
