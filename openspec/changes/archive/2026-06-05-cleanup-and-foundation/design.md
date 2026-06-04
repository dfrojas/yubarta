## Context

The current `yubarta/` package has drifted from the project spec: the entrypoint is broken, two `Alert` models conflict, dead code obscures intent, and the folder layout groups code by technical role (api_server, drivers, models) rather than by capability (ingestion, scanner, orchestrator, agent). This makes it hard to know where new capability code belongs and how boundaries are enforced.

This design covers only structural changes: folder layout, canonical domain model, and seam interfaces. No runtime behavior changes.

## Goals / Non-Goals

**Goals:**
- A folder layout where each capability has a clear home
- One canonical `Signal` type shared across all capabilities
- `Protocol` interfaces at the three seams that vary across deployment contexts (storage, messaging, SSH)
- A working `main.py` entrypoint
- All orphaned code deleted

**Non-Goals:**
- Implementing any capability beyond what exists today
- Changing the ingest endpoint logic
- Resolving spec TODOs (queue choice, RAG store, credential resolution)

## Decisions

### Capability-aligned top-level layout, not horizontal layers

```
yubarta/
  domain/        # canonical shared types: Signal, Incident
  infra/         # shared low-level adapters: db/, cache/, ssh/, messaging/
  ingestion/     # webhook route + normalization (currently api_server/ + models/)
  scanner/       # probe runner (future)
  director/      # state machine (currently director/)
  agent/         # diagnosis + RAG (future)
  chatops/       # Telegram/Slack (future)
  main.py
```

**Why over horizontal layers (`api_server/`, `drivers/`, `models/`):** When working on a capability (e.g., ingestion), all relevant code is in one place. Horizontal layers scatter a single capability across multiple folders and give no guidance on where new code belongs.

**Why `infra/` for shared adapters:** Storage, cache, SSH, and messaging are used by multiple capabilities. They don't belong to any one capability folder, but they're not domain logic either. `infra/` is honest about what they are: implementation details.

### `Signal` as the canonical internal type

A `Signal` is the normalized representation of any event entering the remediation loop. It has no source-specific fields — those stay in the adapter that produced it.

Minimum fields: `id` (idempotency key), `fingerprint` (dedup key), `status` (`firing` | `resolved`), `source` (`webhook` | `scanner` | `chatops`), `labels` (arbitrary key-value, used for target matching), `fired_at`, `raw` (original payload for diagnosis context).

**Why not keep `Alert`:** The current `Alert` model embeds Confluent-specific fields (`group_id`, `topic`, `lag`). A model that leaks source details into the shared domain is not a normalization boundary — it's a naming convention. `Signal` enforces the boundary by design.

### Protocol interfaces at three seams only

Three seams are declared as `Protocol` in `domain/ports.py`:
- `SignalStore` — add/get/update a signal (implemented by SQLAlchemy in `infra/db/`)
- `MessageBus` — publish a signal (implemented by Kafka in `infra/messaging/`, or a simple asyncio queue)
- `RemoteExecutor` — run a command on a target (implemented by SSH in `infra/ssh/`)

**Why only three:** Hexagonal architecture applied everywhere adds indirection without benefit. These three are the only seams where: (a) the test vs production implementation meaningfully differs, and (b) swapping the implementation is plausible (e.g., Kafka → lighter queue, SSH → container exec).

The LLM, MCP runtime, and ChatOps bot are not behind Protocol interfaces — they are external services and tested via integration, not fakes.

### Kafka is the message bus

The `MessageBus` Protocol is implemented by Kafka. The existing `infra/messaging/` Kafka producer and admin client are kept and moved. The asyncio-queue alternative is off the table.

**Why:** The project is explicitly a learning vehicle for distributed-systems patterns. Kafka is one of them. The single-node scope doesn't change this — the learning goal does.

### `main.py` fixed to use current router path

The broken import (`yubarta.entrypoints.api_server.v1.router`) is replaced with the current path (`yubarta.ingestion.router`). Lifespan wiring updated to match the new layout.

## Risks / Trade-offs

- **Import churn across tests** — reorganizing modules breaks all existing test imports. Mitigation: update tests in the same PR as the module moves; `make check` catches misses.
- **`infra/` may accumulate too broadly** — with no capability owner, `infra/` risks becoming a catch-all. Mitigation: each module in `infra/` must be used by at least two capabilities to justify living there; if only one capability uses it, it moves into that capability's folder.
- **`domain/ports.py` as a shared contract** — changes to a Protocol break all implementations. This is intentional: the Protocol is the contract, and breaking it surfaces coupling explicitly rather than silently.

## Migration Plan

1. Delete orphaned files and directories (`old/`, `frontend/`, `examples/`, Rust files, dead Python stubs)
2. Create new folder layout (empty `__init__.py` files)
3. Move existing modules to new locations, updating intra-package imports
4. Define `Signal` in `domain/signal.py`, delete `models/alerts.py`
5. Define `Protocol` interfaces in `domain/ports.py`
6. Fix `main.py` import
7. Update `pyproject.toml` packages entry if needed
8. Update test imports, run `make test` and `make check`

No rollback strategy needed — this is a local structural refactor with no deployed state.

## Open Questions

- **`ingestion/` owns the current ingest route:** The existing `/api/v1/ingest/confluent` endpoint moves to `ingestion/`. Its logic is not changed here, but it will become visibly wrong (Confluent-specific) — flagged for `signal-ingestion` to fix.
