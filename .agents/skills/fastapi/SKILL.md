---
name: fastapi
description: FastAPI rules for Yubarta. Use when you build or change an HTTP API with Pydantic v2, routers, dependency injection, and bearer auth.
---

# FastAPI

These rules come from the official FastAPI guide and from production experience. They cover only the patterns that Yubarta uses.

## Structure

- Use one package for each capability. Organize by domain, not by file type. Use `router.py`, `schemas.py`, `routes/`, `dependencies.py`, and `app.py`.
- Keep the app factory in `app.py`. Put the routes in modules. Each module has one `APIRouter` at module level. Do not use functions inside functions. Do not put route definitions in the factory.

## Versions

- Put business routes under a version: `APIRouter(prefix="/api/v1", tags=[...])`.
- Keep `/health` without a version and without auth. Orchestrators use it.
- Do not remove a path without a warning. Change the callers, or add a new version.

## App factory and life cycle

- Use `@asynccontextmanager` for startup and shutdown. Do not use `@app.on_event`.
- Accept a runtime that you already built. Set `manage_runtime=True`. Then the lifespan controls the runtime. A test can build an app around a runtime that the test controls.
- Put shared state on `app.state`. Do not use module globals.
- The runtime owns the services. This is not a FastAPI task. Refer to the `composition-root` skill.

## Routers

- Put `prefix`, `tags`, and shared `dependencies=[Depends(...)]` on the router. Do not put them in `include_router()`.
- Put all versioned routers together in one place. Apply auth one time at that level.
- Use one HTTP operation for each function. A handler changes a request into a response and calls a service. Do not put business logic in a route.

## Dependencies

- Always use `Annotated`. Give a name to a dependency that you use again:

  ```python
  RuntimeDep = Annotated[YubartaRuntime, Depends(get_runtime)]
  ```

- Use a `yield` dependency for a resource that needs cleanup (a session or a repository).
- Use `Path`, `Query`, and `Header` in `Annotated` for parameters.

## Pydantic and responses

- Keep the request and response schemas apart from the persistence models.
- Do not use `...` (Ellipsis) for a required field. A field without a default is required.
- Use `Field(...)` to set limits. Let FastAPI make the OpenAPI document.
- Use a return type. Use `response_model` only if the public schema is different from the return value.
- Set `model_config = ConfigDict(from_attributes=True)` to make a response from an ORM row. Then you do not need code that copies each field.
- Use `datetime`, not a text string.
- Do not use the Pydantic `RootModel`. Use `Annotated[list[T], Body()]`.
- Do not use `ORJSONResponse` or `UJSONResponse`. A return type does the serialization.

## Security

- Make bearer auth a dependency. Do not call an auth function in each route. Use `HTTPBearer(auto_error=False)` and a router-level `Depends(require_bearer)`.
- Compare tokens with `hmac.compare_digest`. Do not use `==`.
- Read the secret one time at app build. Read it from an environment variable. Do not write a secret in the code.
- Stop the start if auth is on and the secret is missing.
- On a failure, raise `HTTPException(401, ..., headers={"WWW-Authenticate": "Bearer"})`.
- A static bearer token is a temporary solution. Use JWT with users when you need identity.

## Async

- Use `async def` only for real I/O. For other work, use `def`. FastAPI runs `def` in a thread pool.
- Do not block the event loop in `async def`. Do not use `time.sleep()` or a sync database call.

## Errors

- Use a correct status code and a clear `detail`. Do not send a 500 for a client error.

## Tests

- Use `httpx.AsyncClient` with `ASGITransport(app=app)` to test routes.
- Test auth: `/health` is open; no token or a bad token gives 401; a good token gives 200. Also test the start with a missing secret.
- Use fixtures, not helper functions. Put the tests in `tests/unit` and `tests/integration`.

## Tools

- `ruff check` is the gate. Run it before you say the work is done.
