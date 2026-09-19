"""Keep technology dependencies out of the agreed inner layers."""

import ast
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    ("package", "forbidden"),
    [
        (
            "core",
            (
                "yubarta.controllers",
                "yubarta.drivers",
                "yubarta.entrypoints",
                "yubarta.runtime",
                "yubarta.config",
                "sqlalchemy",
                "asyncssh",
                "httpx",
                "fastapi",
            ),
        ),
        (
            "controllers",
            ("yubarta.drivers", "yubarta.entrypoints", "yubarta.runtime", "sqlalchemy", "asyncssh", "httpx", "fastapi"),
        ),
        ("config", ("yubarta.controllers", "yubarta.drivers", "yubarta.entrypoints", "yubarta.runtime")),
        ("entrypoints/api_server", ("yubarta.drivers.db", "sqlalchemy")),
    ],
)
def test_import_boundaries(package: str, forbidden: tuple[str, ...]) -> None:
    root = Path(__file__).resolve().parents[2] / "yubarta"
    violations: list[str] = []
    for path in (root / package).rglob("*.py"):
        with path.open() as source:
            tree = ast.parse(source.read())
        for node in ast.walk(tree):
            imports: list[str] = []
            if isinstance(node, ast.Import):
                imports = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                imports = [node.module or ""]
            for module in imports:
                if any(module == prefix or module.startswith(f"{prefix}.") for prefix in forbidden):
                    violations.append(f"{path.relative_to(root)}:{node.lineno}: {module}")
    assert not violations, "\n".join(violations)
