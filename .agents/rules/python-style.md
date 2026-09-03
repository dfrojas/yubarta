---
name: python-style
scope: python
glob: "**/*.py"
description: Python style defaults for Yubarta. Typing, error handling, naming, imports.
---

# Python Style

Apply to all `.py` files. Several of these (line length, import ordering) are already enforced by `ruff` (see `pyproject.toml`); they're restated here for context, not duplicated enforcement, run `poetry run ruff check .` as the actual gate.

## Rules

- **Pin dependencies to the full `major.minor.patch`** in Poetry, never just major or major.minor.
- **Use current Python features** rather than patterns that predate them.
- **Handle errors at the top of a function with early returns**, not deeply nested conditionals.
- **Use specific exception types**, both when raising and when catching. `except Exception:` only as a last resort at a branch boundary, never as the default.
- **Custom error types and real logging**, not silent `pass` or bare prints.
- **Descriptive variable names.** No single-letter names like `i` or `j`, even in short loops. or stms for statement. Always completed names.
- **Type everything a reader would need to understand the contract**, not just what mypy strictly requires.
- **Double quotes and f-strings** for strings and interpolation (matches `ruff format`'s configured quote style).
- **Imports follow isort precedence**: standard library, third-party, local, already enforced by `ruff`'s `I` rule.
- **Docstrings only where the *why* isn't obvious from the name.** A function called `is_admin` doesn't need one explaining what it does; a function with a non-obvious invariant or workaround does.
- **Context managers (`with`) for file operations and locks.**
- **No mutable default arguments.**
- **No global variables.**
- **`@dataclass` for simple data containers; Pydantic only for data that needs to serialize/deserialize** (API payloads, config, persisted models). Don't reach for Pydantic just for internal structure.
- **List comprehensions where they're actually more readable**, not as a reflex; a multi-condition comprehension that needs a comment to explain itself should be a loop instead.
