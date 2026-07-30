## MODIFIED Requirements

### Requirement: Protocol interfaces declared at real seams
`yubarta/domain/ports.py` SHALL declare `Protocol` interfaces for the three seams where implementation varies between test and production: storage, messaging, and remote execution. No other seams require a Protocol.

#### Scenario: Storage seam is declared as a Protocol
- **WHEN** `domain/ports.py` is inspected
- **THEN** an `IncidentStore` Protocol exists covering incident creation, guarded state transition, remediation-attempt recording and completion, approval resolution, and the history reads, and no `SignalStore` Protocol exists

---

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

#### Scenario: Unimplemented capabilities have no folder
- **WHEN** the package is inspected
- **THEN** no folder under `yubarta/` is empty or contains only an empty `__init__.py`, and none of the reserved names (`director/`, `scanner/`, `agent/`, `chatops/`) exists

## ADDED Requirements

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
