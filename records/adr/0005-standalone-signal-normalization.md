# 5. Standalone signal normalization

Date: 2026-07-10

## Status

Accepted

## Context

`signal-ingestion` needed a way to turn an Alertmanager webhook payload into a `Signal`. The conventional Python pattern for this is an alternate constructor: `Signal.from_alertmanager(payload)`. It is discoverable (it shows up on `Signal` itself) and is how most Python codebases would reach for this.

ADR 0003 already established that `Signal` is the canonical internal type specifically because it carries no source-specific fields (that was the whole point of replacing the old `Alert` model, which had Confluent-specific fields baked in). A `from_alertmanager()` classmethod on `Signal` would quietly reintroduce the same problem one level up: `Signal` (a domain type) would need to know the shape of Alertmanager's payload (an infrastructure/external-system concern) in order to implement that method, even though the resulting object itself stays clean.

## Decision

Normalization lives in a standalone function, `normalize_alertmanager()` in `yubarta/ingestion/normalizers/alertmanager.py`, not as a method on `Signal`. `yubarta/domain/signal.py` has no knowledge of any source format.

This is a dependency-direction argument, not a style preference: `ingestion/` is allowed to depend on `domain/` (it imports `Signal` and constructs one), but `domain/` must never depend on `ingestion/` or know about any particular source's payload shape. A classmethod constructor on `Signal` would create that dependency in the wrong direction, however small it looks for one source.

This decision generalizes to every future signal source. The proactive scanner and any vendor integration (e.g. Grafana, when that stage happens) each get their own `normalize_*()` function in their own adapter module, never a method added to `Signal`.

## Consequences

### Positive
- `yubarta/domain/` stays genuinely source-agnostic as more ingestion adapters are added; `Signal` never accumulates one constructor per source.
- Each adapter's normalization logic is testable and replaceable in isolation, without touching the domain module.

### Negative
- Slightly less discoverable than a classmethod: a reader looking at `Signal` won't find a list of "ways to construct one" on the class itself, and has to know to look in `ingestion/normalizers/`.
- Relies on convention rather than the type system to keep future adapters from taking the shortcut of adding a classmethod under time pressure; this ADR is the enforcement mechanism until/unless it is checked structurally.
