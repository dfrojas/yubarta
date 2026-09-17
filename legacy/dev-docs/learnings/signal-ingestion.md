# Learning Note: signal-ingestion

## Normalizer as standalone function, not a classmethod

The team discussed `Signal.from_alertmanager()` vs a standalone `normalize_alertmanager()` function. The classmethod is the conventional Python pattern for alternate constructors, and it's discoverable. We chose the standalone function because the real argument is about dependency direction: if `Signal` has `from_alertmanager()`, the domain layer depends on knowledge of an external system's payload format. Infrastructure concerns leak into the core. The standalone function in `ingestion/normalizers/alertmanager.py` keeps the dependency direction right: ingestion knows about Alertmanager; the domain doesn't. The spec reinforcement ("Signal has no source-specific fields") was noted but explicitly set aside — the architectural argument stands on its own.

## Idempotency key is per-event, not per-condition

`Signal.id` is derived from `fingerprint + fired_at`. This means the same disk-full condition firing twice produces two distinct signals (different `fired_at`), which is correct — those are two separate incidents. If Alertmanager retries the same webhook, `fired_at` (from `startsAt`) is unchanged and the id is stable, so the duplicate is silently dropped by `setdefault`. Using `fingerprint` alone as the key would have collapsed all firings of the same condition into one record, silently dropping real incidents.

## FastAPI dependency injection for store isolation

The `get_signal_store` dependency function returns a module-level singleton `InMemorySignalStore`. Tests override it with `app.dependency_overrides[get_signal_store] = lambda: store` and a fresh `InMemorySignalStore` per test, giving full isolation without any global state leaking between tests. The route imports only the `SignalStore` Protocol, never the concrete implementation, which keeps the seam clean.

## In-memory idempotency is process-scoped

The `InMemorySignalStore` provides idempotency only within a single process lifetime. A restart resets the store and could re-process the same Alertmanager webhook if it fires again before the Postgres store is wired (stage 3). This was accepted as a known limitation for the ingestion milestone.

## httpx version pinning

FastAPI 0.100.1 uses Starlette 0.27.0, which uses `httpx`'s `app=` shortcut in `TestClient`. This parameter was removed in `httpx 0.28`. Had to pin `httpx<0.28` in dev dependencies. When upgrading FastAPI in the future, revisit this constraint — newer starlette uses `transport=ASGITransport(app=...)` and works with httpx 0.28+.

## main.py simplification

The previous `main.py` initialized Kafka and Postgres in the lifespan context. Both are out of scope until stages 3 and later. Initializing them in this stage caused import errors in tests. Simplified `main.py` to just wire the ingestion router. Each stage will add its own initialization concern.
