# Learnings: cleanup-and-foundation

## Folder layout: capability-aligned over horizontal layers

Organizing by `ingestion/`, `director/`, `scanner/` etc. instead of `drivers/`, `models/`, `api_server/` makes it immediately clear where new code belongs. The previous layout scattered a single capability across three folders with no guidance on boundaries.

The one nuance: shared infrastructure (DB sessions, Kafka client, Redis, SSH) that no single capability owns goes into `infra/`. The rule of thumb: if only one capability uses it, it lives inside that capability's folder. If two or more use it, it lives in `infra/`.

## Signal vs Alert

The old `Alert` model had Confluent-specific fields (`group_id`, `topic`, `lag`) baked in. That means the "normalized" model was actually source-specific — the opposite of normalization. `Signal` enforces the boundary by design: no source fields, only what every source has in common (`status`, `source`, `labels`, `fired_at`, `raw`). Source-specific parsing stays in the adapter that produces the Signal.

The `raw` field matters: the diagnosis agent needs the original payload to reason over unstructured evidence. Storing it on Signal avoids a re-fetch later.

## @computed_field and mypy

Pydantic's `@computed_field` stacked on `@property` is valid at runtime but mypy doesn't understand the decorator order — it reports `prop-decorator` errors. The fix is `# type: ignore[prop-decorator]` on the `@computed_field` line. This is a known mypy/Pydantic gap, not a logic error.

## Surprising things

- `main.py` was importing from `yubarta.entrypoints.api_server.v1.router` — a path that only existed in `old/`. The app couldn't start. This went unnoticed because the tests used mocked infrastructure and never actually started the app.
- The `drivers/` naming was backwards relative to hexagonal architecture convention (where "drivers" means inbound, not outbound). Renaming to `infra/` removes that confusion.
- `sessions.py` called `db.get_session()` but that method was commented out in `Database`. The session factory was always there; the method was just a thin wrapper that was never finished.
