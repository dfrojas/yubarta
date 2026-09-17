## ADDED Requirements

### Requirement: Capability-aligned folder layout
The codebase SHALL be organized by capability under `yubarta/`, not by technical role. Each top-level module corresponds to one capability from the project spec or to a shared infrastructure concern.

The required top-level layout is:
```
yubarta/
  domain/       # canonical shared types and port interfaces
  infra/        # shared low-level adapters (db, cache, ssh, messaging)
  ingestion/    # webhook normalization and ingest route
  director/     # remediation state machine
  scanner/      # probe runner and threshold evaluation
  agent/        # diagnosis agent and RAG
  chatops/      # Telegram/Slack bot
  main.py       # application entrypoint
```

#### Scenario: New capability code has an unambiguous home
- **WHEN** a developer adds code for a new capability (e.g., scanner)
- **THEN** there is exactly one folder under `yubarta/` where that code belongs

#### Scenario: Shared infrastructure adapters live in infra/
- **WHEN** a low-level adapter (DB session, Kafka client, Redis client, SSH client) is used by more than one capability
- **THEN** it lives under `yubarta/infra/` and not inside any single capability folder

#### Scenario: No orphaned modules at the root
- **WHEN** the package is inspected
- **THEN** no Python modules exist directly under `yubarta/` except `main.py` and `__init__.py`

---

### Requirement: Working application entrypoint
`yubarta/main.py` SHALL import only from paths that exist in the current package layout and start without import errors.

#### Scenario: Application starts cleanly
- **WHEN** `uvicorn yubarta.main:app` is run
- **THEN** the process starts without `ImportError` or `ModuleNotFoundError`

---

### Requirement: No dead code in the repository
All code in the repository SHALL map to at least one capability in the project spec. Files with no capability mapping SHALL be deleted.

The following are confirmed orphaned and SHALL be removed:
- `old/` (prior architecture attempt)
- `frontend/` (no frontend capability)
- `examples/` (early sketches)
- `yubarta/director/src/main.rs` and `yubarta/director/Cargo.toml` (Rust, project stack is Python)
- `yubarta/director/director.py` (empty Kafka stub, superseded by `director/` capability)

#### Scenario: Repository contains no Rust files
- **WHEN** the repository is scanned for `.rs` and `Cargo.toml` files
- **THEN** none are found

#### Scenario: Repository contains no old/ directory
- **WHEN** the repository root is listed
- **THEN** no `old/` directory exists

---

### Requirement: Protocol interfaces declared at real seams
`yubarta/domain/ports.py` SHALL declare `Protocol` interfaces for the three seams where implementation varies between test and production: storage, messaging, and remote execution. No other seams require a Protocol.

#### Scenario: Storage seam is declared as a Protocol
- **WHEN** `domain/ports.py` is inspected
- **THEN** a `SignalStore` Protocol exists with at minimum `add` and `get` methods

#### Scenario: Messaging seam is declared as a Protocol
- **WHEN** `domain/ports.py` is inspected
- **THEN** a `MessageBus` Protocol exists with at minimum a `publish` method

#### Scenario: Remote execution seam is declared as a Protocol
- **WHEN** `domain/ports.py` is inspected
- **THEN** a `RemoteExecutor` Protocol exists with at minimum an `exec` method

#### Scenario: Implementations satisfy their Protocol
- **WHEN** the SQLAlchemy storage, Kafka message bus, and SSH executor are type-checked
- **THEN** `make check` passes with no Protocol compatibility errors
