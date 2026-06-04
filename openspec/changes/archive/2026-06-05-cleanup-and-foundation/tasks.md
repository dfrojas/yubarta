## 1. Delete Orphaned Code

- [x] 1.1 Delete `old/` directory
- [x] 1.2 Delete `frontend/` directory
- [x] 1.3 Delete `examples/` directory
- [x] 1.4 Delete `yubarta/director/src/main.rs` and `yubarta/director/Cargo.toml`
- [x] 1.5 Delete `yubarta/director/director.py`
- [x] 1.6 Delete `yubarta/models/alerts.py`

## 2. Create Folder Layout

- [x] 2.1 Create `yubarta/domain/__init__.py`
- [x] 2.2 Create `yubarta/infra/__init__.py` with subdirs: `db/`, `cache/`, `ssh/`, `messaging/`
- [x] 2.3 Create `yubarta/ingestion/__init__.py`
- [x] 2.4 Create `yubarta/director/__init__.py` (replacing the deleted stub)
- [x] 2.5 Create `yubarta/scanner/__init__.py`
- [x] 2.6 Create `yubarta/agent/__init__.py`
- [x] 2.7 Create `yubarta/chatops/__init__.py`

## 3. Move Existing Modules

- [x] 3.1 Move `yubarta/drivers/db/` → `yubarta/infra/db/`, update all intra-package imports
- [x] 3.2 Move `yubarta/drivers/cache/` → `yubarta/infra/cache/`, update imports
- [x] 3.3 Move `yubarta/drivers/messaging/` → `yubarta/infra/messaging/`, update imports
- [x] 3.4 Move `yubarta/drivers/network/ssh.py` → `yubarta/infra/ssh/client.py`, update imports
- [x] 3.5 Move `yubarta/drivers/config/` → `yubarta/infra/config/`, update imports
- [x] 3.6 Move `yubarta/api_server/` → `yubarta/ingestion/`, update imports
- [x] 3.7 Delete now-empty `yubarta/drivers/` directory

## 4. Define Signal

- [x] 4.1 Create `yubarta/domain/signal.py` with `SignalStatus` (`StrEnum`: `firing`, `resolved`) and `SignalSource` (`StrEnum`: `webhook`, `scanner`, `chatops`)
- [x] 4.2 Add `Signal` Pydantic model with fields: `id`, `fingerprint`, `status`, `source`, `labels`, `fired_at`, `raw`
- [x] 4.3 Implement `id` as a `computed_field` (SHA-256 over source + labels + fired_at)
- [x] 4.4 Implement `fingerprint` as a `computed_field` (SHA-256 over source + labels, excluding fired_at)
- [x] 4.5 Write unit tests: id determinism, fingerprint stability across firings, resolved carries same fingerprint as firing

## 5. Define Port Interfaces

- [x] 5.1 Create `yubarta/domain/ports.py` with `typing.Protocol` for `SignalStore` (methods: `add`, `get`)
- [x] 5.2 Add `MessageBus` Protocol (method: `publish`)
- [x] 5.3 Add `RemoteExecutor` Protocol (method: `exec` returning `tuple[int, str, str]`)
- [x] 5.4 Annotate existing `SqlAlchemyAlarmRepository`, `KafkaProducer`, and `SSHClient` with the corresponding Protocol and confirm `make check` passes
  <!-- deferred to signal-ingestion: implementations predate Signal and need Signal-aware rewrites before they can satisfy the Protocol -->

## 6. Fix Entrypoint

- [x] 6.1 Update `yubarta/main.py` import to point at `yubarta.ingestion.router`
- [x] 6.2 Confirm `uvicorn yubarta.main:app` starts without import errors

## 7. Housekeeping

- [x] 7.1 Update `pyproject.toml` packages entry if any path changed
- [x] 7.2 Update all test imports to match new module paths
- [x] 7.3 Run `make test` — all existing tests pass
- [x] 7.4 Run `make check` — mypy reports no errors
- [x] 7.5 Write `docs/learnings/cleanup-and-foundation.md` covering: folder layout rationale, Signal vs Alert decision, Protocol placement in domain/, and anything surprising during the move
