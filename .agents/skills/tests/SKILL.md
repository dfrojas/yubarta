---
name: tests
description: Structure tests
---

# Pytest Fixtures

Applies to everything under `tests/`. This skill overrides the older `conftest.py` fixture rules in the `python` and `e2e-testing` skills.

## Location and registry

- Put shared fixtures in `tests/fixtures/<domain>.py`.
- Keep `tests/conftest.py` as registry only with a `pytest_plugins` list.
- Keep no fixtures in test modules.
- Keep no extra `conftest.py` for E2E, unit or integration

Example registry:

```python
pytest_plugins = [
    "tests.fixtures.postgres",
    "tests.fixtures.ssh",
    "tests.fixtures.api",
    "tests.fixtures.e2e",
]
```

## Categorization

- One module per purpose:
  - `postgres.py`: cluster, template, per-test DB, session factory.
  - `ssh.py`: fake SSH target.
  - `api.py`: app and live server.
  - `e2e.py`: Docker sandbox plus server process under test.
  - `ports.py`: `free_port()` helper.
- Keep helpers out of fixture modules. `docker_sandbox.py`, `support.py`, and `fake_ssh.py` stay as helpers, not fixtures.
- Keep one E2E module while E2E covers one scenario. Split only when a second scenario with distinct setup exists.


## Typing and style

- Type all fixture parameters and returns. Use `AsyncIterator`, `Iterator`, `pytest.FixtureRequest`, `pytest.MonkeyPatch`, and `Path`.
- Keep no `# type: ignore[no-untyped-def]` in fixture code or in fixture consumers touched by the change.
