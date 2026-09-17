## Why

The existing codebase cannot start (broken import in `main.py`), contains two conflicting `Alert` models, dead code with no mapping to the current spec (Rust director, frontend, `old/` directory, Confluent-specific examples), and has no folder structure aligned to the spec's capability list. Every subsequent capability change would be building on a fractured, misleading foundation.

## What Changes

- **BREAKING** — Delete `old/` (prior clean-architecture attempt, superseded by current spec)
- **BREAKING** — Delete `yubarta/director/src/main.rs` and `Cargo.toml` (Rust director, project stack is Python)
- **BREAKING** — Delete `frontend/config.js` (no frontend in the current spec)
- **BREAKING** — Delete `examples/` (early sketch, no mapping to any current capability)
- **BREAKING** — Delete `yubarta/models/alerts.py` (Confluent-specific `Alert`, replaced by canonical `Signal`)
- **BREAKING** — Delete `yubarta/director/director.py` (stub Kafka consumer, replaced by `orchestrator/` capability)
- Fix broken import in `yubarta/main.py` (points to `yubarta.entrypoints.api_server.v1.router`, which no longer exists)
- Introduce capability-aligned folder layout under `yubarta/`
- Introduce the canonical internal `Signal` model in `yubarta/domain/`
- Introduce `Protocol` interfaces for the three real seams: storage, messaging, SSH

## Capabilities

### New Capabilities

- `project-structure`: The folder layout, module naming conventions, and layer boundaries that all other capabilities build on. Not a runtime capability — a structural one.
- `domain-signal`: The canonical internal `Signal` model that every capability produces or consumes. Defines the normalized representation of an event entering the system, independent of source (webhook, scanner, ChatOps).

### Modified Capabilities

None — no existing specs exist yet.

## Non-goals

- This change does not implement any runtime behavior. No ingestion logic, no scanning, no agent, no state machine.
- It does not resolve any spec `TODO`s (queue choice, RAG store, inventory label-matching, credential resolution). Those belong to their respective capability changes.
- It does not wire the `Signal` model into any endpoint — that belongs to `signal-ingestion`.

## Impact

- All existing `yubarta/` Python modules are reorganized; imports across the codebase will break and need updating.
- `pyproject.toml` packages list updated to reflect new layout.
- `Makefile` targets may need path updates.
- Tests under `tests/` reference old module paths — will need updates in lockstep.
- No external API surface changes (the ingest endpoint path stays the same).
- No new dependencies added.
