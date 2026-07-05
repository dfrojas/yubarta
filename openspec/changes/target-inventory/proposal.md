## Why

Signals arriving from ingestion carry only labels — Yubarta has no notion yet of which host those labels refer to, how to connect to it, or which remediations are permitted there. Stage 2 of the refactor roadmap introduces the target inventory: a config-driven map from label sets to connectable targets, so later stages (remote execution, remediation loop) have something concrete to act on.

## What Changes

- Define the `inventory.yaml` schema: `groups` (shared connection defaults) and `targets` (per-host `group`, `address`, `labels`, `credential` reference, `remediations` allowlist).
- Add a loader that reads and validates `inventory.yaml` into typed models at startup, failing fast on malformed config.
- Add label-matching: given a `Signal`, resolve the single `Target` whose labels are a subset of the signal's labels. No match or more than one match is not resolved silently — the caller gets an explicit ambiguous/no-match result to escalate on, never a guessed target.
- `credential` is parsed and stored as an opaque reference string (e.g. `sops://secrets/hosts/x.yaml#key`) only. Actually resolving it to a usable secret is out of scope here (see Non-goals).

## Non-goals

- **Credential resolution.** Resolving `sops://...` references to short-lived, least-privilege secrets is the `remote-execution` stage's job. This stage only validates the reference is a well-formed string and passes it through.
- **Scan/probe execution.** The `scan.commands`/`checks` block (periodic vs streaming inference, threshold eval) belongs to `proactive-scanner`. This stage's loader may parse the block into a model for schema completeness but does not execute or evaluate it.
- **SSH/remote execution wiring.** No connections are opened in this stage.
- **Audit trail.** Deferred to `remote-execution`, once there are executed actions to audit.

## Capabilities

### New Capabilities
- `target-inventory`: `inventory.yaml` schema, loader/validator, and signal-label-to-target matching with explicit no-match/ambiguous-match handling.

### Modified Capabilities
(none — `signal-ingestion` and `domain-signal` are unaffected; this stage only reads `Signal.labels`)

## Impact

- New module `yubarta/inventory/` (schema, loader, matcher), following the `yubarta/ingestion/` layout convention.
- New `Target`/`InventoryGroup` Pydantic models and an `InventoryStore`-style Protocol port in `yubarta/domain/ports.py` if a seam is warranted.
- New `inventory.yaml` (dev fixture) plus a documented location for the real file (config-driven, not committed).
- No changes to existing ingestion routes or the `Signal` model.
- Resolves the spec's "label-matching is unspecified" TODO (docs/yubarta-spec.md:146); leaves credential resolution and scan/threshold TODOs open for later stages.
