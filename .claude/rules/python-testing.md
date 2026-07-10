---
name: python-testing
scope: python
glob: "**/tests/**"
description: Test conventions for Yubarta. pytest, fixtures, folder layout, unit vs integration.
---

# Testing

Apply to everything under `tests/`.

## Rules

- **pytest**, not unittest-style classes.
- **Prefer fixtures over ad-hoc helper functions** for anything reused across tests.
- **`conftest.py` is the config/fixture file** for a directory's shared setup, not a dumping ground.
- **Folder layout mirrors use cases**, not implementation modules. `tests/unit/` and `tests/integration/` split by what's being verified, matching the project's existing layout.
- **Decide unit vs. integration deliberately, per case.** This project prefers integration tests against real/containerized infrastructure over extensive unit-test fakes (see `records/adr/`), a unit test is the exception that needs a reason, not the default.
