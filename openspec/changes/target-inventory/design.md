## Context

`yubarta/ingestion/` normalizes external alerts into `Signal` objects (`yubarta/domain/signal.py`) and stores them idempotently. Nothing downstream yet knows how to turn a `Signal`'s `labels` into a concrete host to act on. `dev-docs/yubarta-spec.md:100-148` sketches an `inventory.yaml` format (`groups` + `targets`, label matching, `sops://` credential references, per-target `remediations` allowlist) and flags label-matching as an open TODO.

This stage builds the inventory schema, a loader, and the label-matching function only. It does not open connections, resolve credentials, or evaluate scan/thresholds — those are `remote-execution` and `proactive-scanner`'s job.

Note: `yubarta/infra/config/` (`FullConfig`/`Remediation` models) is a pre-refactor artifact describing a different, more elaborate remediation-config shape and is not reused here — it predates the capability-aligned restructuring and the simpler `inventory.yaml` contract in the current spec.

## Goals / Non-Goals

**Goals:**
- Typed, validated representation of `inventory.yaml`: `InventoryGroup`, `Target`, `Inventory`.
- A loader that reads the YAML file and raises immediately on missing file, malformed YAML, or schema violation (fail fast at startup, not at first use).
- A `match_target(inventory, signal) -> Target` (or equivalent) function implementing the label-matching rule, with explicit, distinguishable outcomes for "no match" and "ambiguous match" — callers must not silently pick one of several candidates.
- Dev fixture `inventory.yaml` mirroring the spec's example, for local runs and tests.

**Non-Goals:**
- Resolving `credential: sops://...` to an actual secret (`remote-execution`).
- Executing or scheduling `scan.commands`/`checks` (`proactive-scanner`). The loader accepts the block as opaque/typed-but-unused config so the schema doesn't need a breaking change later.
- Wiring inventory lookups into the ingestion webhook or any orchestrator loop — this stage only provides the building blocks.
- Hot-reloading the inventory file; it's read once at process startup.

## Decisions

**Matching rule: signal labels ⊇ target labels, reject on 0 or >1 matches.**
A target matches a signal when every `target.labels` key/value pair is present in `signal.labels` (target labels are a subset of signal labels — extra signal labels, e.g. `severity`, don't prevent a match). This mirrors Kubernetes label-selector semantics, which the spec's example implicitly follows (`service`/`role` on the target vs. a richer label set on the incoming alert).
- Zero matches → raise `NoMatchingTargetError` (subclass of a shared `InventoryMatchError`).
- More than one match → raise `AmbiguousTargetError` with the list of candidate target names, so the caller escalates instead of guessing (per spec: "no match, do not act blindly").
- Alternative considered: exact label-set equality. Rejected — the spec's `java-app-1` example has only 2 labels while real Alertmanager alerts carry many (`alertname`, `severity`, `instance`, ...); requiring equality would never match anything.

**Module layout: `yubarta/inventory/`, mirroring `yubarta/ingestion/`.**
- `schema.py` — `InventoryGroup`, `ScanConfig` (opaque pass-through), `Target`, `Inventory` Pydantic models.
- `loader.py` — `load_inventory(path: str | Path) -> Inventory`, thin `yaml.safe_load` + `Inventory.model_validate`.
- `matcher.py` — `match_target(inventory: Inventory, signal: Signal) -> Target`, plus the two error types.
- `dependencies.py` — `get_inventory()` FastAPI dependency, loading once from a path resolved via `Settings` (mirrors `ingestion/dependencies.py`'s singleton-store pattern), so later stages (webhook, orchestrator) can inject it without re-parsing.

**`credential` stays a plain `str`.**
No `SecretStr`, no eager parsing of the `sops://` scheme. Validating and resolving it is explicitly out of scope; a loose string keeps this stage from committing to a resolution design before `remote-execution` needs one. A `pattern=r"^sops://"` validator would be premature — deferred.

**`groups` resolve into each `Target` at load time, not lazily.**
`Inventory.model_validate` (a `model_validator(mode="after")`) merges each target's `group` defaults (e.g. `transport`, `user`, `port`) into the target, producing a fully-resolved `Target` with no further group lookup needed downstream. Fails validation immediately if a target references an unknown group — consistent with fail-fast loading.

## Risks / Trade-offs

- **Subset-match false positives.** A target with very generic labels (e.g. just `role: api`) could accidentally match unrelated signals. Mitigation: this is a config-authoring concern, not a code concern for this stage — the per-target `remediations` allowlist (already in the schema) is the second guardrail the spec calls for; documented in the dev fixture's comments as an authoring convention (specific labels).
- **No hot-reload** means an inventory change requires a restart. Acceptable for a single-host learning project; revisit only if it becomes a real friction point.
- **Opaque `scan`/`credential` fields** mean this stage's schema will need a real (possibly breaking) shape once `proactive-scanner`/`remote-execution` land. Mitigation: keep those fields typed as loosely as possible now (`ScanConfig` as a pass-through model, `credential: str`) to minimize churn.

## Open Questions

- Should `match_target` support signals that reference multiple targets (e.g. a cluster-wide alert), or is 1 signal → 1 target a hard invariant for the whole system? Deferred until the orchestrator stage surfaces a real case; current scope assumes 1:1.
