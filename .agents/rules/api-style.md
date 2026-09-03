---
name: api-style
scope: api
glob: "yubarta/*/router.py, yubarta/*/routes/**"
description: API design and FastAPI implementation conventions for Yubarta's capability-owned routers.
---

# API Style

Applies to any capability's `router.py` and `routes/` (e.g. `yubarta/ingestion/router.py`, `yubarta/ingestion/routes/`). Each capability owns and versions its own router; there is no central `api_server` module.

## Design

- **Pydantic models for every request and response schema.** No raw dicts crossing the route boundary.
- **Version the API.** Existing routers use an `/api/v1` prefix; keep new ones consistent.
- **Follow the OpenAPI specification**, lean on FastAPI's built-in OpenAPI/JSON Schema generation rather than hand-rolling docs.
- **Rate limiting is a real design concern**, not an afterthought, for any route that accepts external input (webhooks especially).
- **Standard REST error handling**: meaningful status codes, `HTTPException` with a clear detail message, not a generic 500 for everything.

## FastAPI implementation

- **Prefer lifespan context managers over `@app.on_event`** for startup/shutdown.
- **`def` for synchronous work, `async def` for actual I/O-bound work.** Don't mark something `async` just by convention if it never awaits anything.
- **Use FastAPI's dependency injection** for shared resources and state (the existing `get_signal_store`/`get_inventory` singleton-dependency pattern), not module-level globals reached into directly from route handlers.
- **SQLAlchemy 2.0 style** for any ORM usage in a route or its dependencies.
- **CORS configured for local dev**, revisit before anything is exposed beyond localhost.
