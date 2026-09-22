from __future__ import annotations

pytest_plugins = [
    "tests.fixtures.postgres",
    "tests.fixtures.ssh",
    "tests.fixtures.api",
    "tests.fixtures.e2e",
    "tests.fixtures.scanners",
    "tests.fixtures.incidents",
]
