# Capability: Project Structure

## Purpose

Defines the canonical folder layout, application entrypoint, and codebase hygiene rules for the Yubarta package. Ensures code has an unambiguous home, dead code is removed, and protocol seams are declared at the right boundaries.

Also defines what "runnable" means, because green tests turned out not to mean it: the rig
must build, the app must boot, the suite must collect, and a checked-in driver script must
reproduce the capability against the raised stack.

---

## Requirements

### Requirement: Capability-aligned folder layout
The codebase SHALL be organized by capability under `yubarta/`, not by technical role. Each top-level module corresponds to one capability from the project spec or to a shared infrastructure concern.

A capability folder is created when its capability is implemented, never in advance. An empty folder or a folder holding only an empty `__init__.py` is not a placeholder, it is noise, and SHALL be deleted.

Currently implemented:
```
yubarta/
  domain/       # canonical shared types and port interfaces
  infra/        # shared low-level adapters (db, cache, ssh, messaging, config)
  config/       # application settings
  ingestion/    # webhook normalization and ingest route
  inventory/    # target inventory loading and matching
  incident/     # incident models, errors, and read routes
  main.py       # application entrypoint
```

Reserved names for capabilities not yet implemented. These folders SHALL NOT exist until their capability has code:
```
  director/     # remediation state machine
  scanner/      # probe runner and threshold evaluation
  agent/        # diagnosis agent and RAG
  chatops/      # Telegram/Slack bot
```

#### Scenario: New capability code has an unambiguous home
- **WHEN** a developer adds code for a new capability (e.g., scanner)
- **THEN** there is exactly one folder under `yubarta/` where that code belongs, taken from the reserved names above

#### Scenario: Unimplemented capabilities have no folder
- **WHEN** the package is inspected
- **THEN** no folder under `yubarta/` is empty or contains only an empty `__init__.py`, and none of the reserved names (`director/`, `scanner/`, `agent/`, `chatops/`) exists

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
- **THEN** an `IncidentStore` Protocol exists covering incident creation, guarded state transition, remediation-attempt recording and completion, approval resolution, and the history reads, and no `SignalStore` Protocol exists

#### Scenario: Messaging seam is declared as a Protocol
- **WHEN** `domain/ports.py` is inspected
- **THEN** a `MessageBus` Protocol exists with at minimum a `publish` method

#### Scenario: Remote execution seam is declared as a Protocol
- **WHEN** `domain/ports.py` is inspected
- **THEN** a `RemoteExecutor` Protocol exists with at minimum an `exec` method

#### Scenario: Implementations satisfy their Protocol
- **WHEN** the SQLAlchemy storage, Kafka message bus, and SSH executor are type-checked
- **THEN** `make check` passes with no Protocol compatibility errors

---

### Requirement: The dev rig builds and starts from a clean checkout
`docker compose -f docker-compose.dev.yaml build` and `up` SHALL succeed on a clean checkout, and every service defined in the compose file SHALL correspond to code that exists in the repository.

The `cleanup-and-foundation` change deleted the Rust director sources but left the `rust-director` Dockerfile stage and the `director` compose service that build from them, so the rig has been unbuildable since. A compose service pointing at deleted sources is the same category of problem as a module importing a deleted symbol, and the same requirement should catch both.

#### Scenario: No compose service builds from deleted sources
- **WHEN** the compose file is inspected against the repository contents
- **THEN** every service's build context and dockerfile target reference paths that exist

#### Scenario: Repository contains no Rust build stages
- **WHEN** the `Dockerfile` is scanned
- **THEN** it contains no `rust` base image or `cargo` invocation, consistent with the existing no-Rust-files requirement

---

### Requirement: The test suite collects without import errors
`pytest` SHALL collect the full suite with no import or collection errors, and `tests/conftest.py` SHALL import only symbols that exist in the package.

A collection error in a shared `conftest.py` fails every test in the tree, including tests unrelated to the broken import, so it hides the state of the whole suite rather than one case.

#### Scenario: Shared fixtures import only live symbols
- **WHEN** `pytest --collect-only` is run
- **THEN** it reports zero errors

---

### Requirement: A checked-in driver script exercises the stage end-to-end
Each implemented capability SHALL be exercisable against the raised stack by a checked-in script under `dev/`, not by an ad-hoc manual command that leaves no reusable artifact.

#### Scenario: The reactive path can be driven end-to-end
- **WHEN** the stack is raised, migrations are applied, and the ingestion driver script is run
- **THEN** it posts a fake Alertmanager alert, and reports back the incident that was created for it, read from Postgres rather than echoed from the request
