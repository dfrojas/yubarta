## 1. Cleanup

- [x] 1.1 Delete `yubarta/ingestion/routes/ingest.py` (old stub with commented-out Kafka/Redis logic)
- [x] 1.2 Remove the `ingest` import and `router.include_router(ingest.router)` line from `yubarta/ingestion/router.py`

## 2. Normalizer

- [x] 2.1 Create `yubarta/ingestion/normalizers/__init__.py`
- [x] 2.2 Create `yubarta/ingestion/normalizers/alertmanager.py` with `normalize_alertmanager(payload: dict) -> list[Signal]` that maps each alert to a `Signal` per the field mapping in the spec

## 3. In-Memory Store

- [x] 3.1 Create `yubarta/ingestion/store.py` with `InMemorySignalStore` implementing the `SignalStore` Protocol (dict-backed, keyed by `signal.id`)
- [x] 3.2 Create `yubarta/ingestion/dependencies.py` with `get_signal_store()` returning the singleton `InMemorySignalStore`

## 4. Webhook Route

- [x] 4.1 Create `yubarta/ingestion/routes/webhook.py` with `POST /alertmanager` route that calls the normalizer, stores each signal idempotently, and returns 202 with `signal_ids`
- [x] 4.2 Update `yubarta/ingestion/router.py` to mount the webhook router at `/webhook`

## 5. App Wiring

- [x] 5.1 Verify `yubarta/main.py` already includes the ingestion router; add it if missing

## 6. Tests

- [x] 6.1 Create `tests/ingestion/test_normalizer.py` — unit tests for `normalize_alertmanager`: single alert, resolved status, multiple alerts, deterministic id
- [x] 6.2 Create `tests/ingestion/test_webhook.py` — integration tests using FastAPI `TestClient`: valid payload accepted, empty alerts list, duplicate submission returns 202 without double-store, dependency override with fresh `InMemorySignalStore`

## 7. Learning Note

- [x] 7.1 Write `docs/learnings/signal-ingestion.md` covering: normalizer-vs-classmethod tradeoff, in-memory idempotency scope, FastAPI dependency injection pattern used, and anything surprising discovered during implementation
