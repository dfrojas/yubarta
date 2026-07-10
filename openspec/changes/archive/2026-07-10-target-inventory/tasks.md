## 1. Schema

- [x] 1.1 Create `yubarta/inventory/__init__.py`
- [x] 1.2 Create `yubarta/inventory/schema.py` with `InventoryGroup` (transport, user, port), `ScanConfig` (opaque pass-through: interval, commands, checks — no execution/evaluation logic), `Target` (group, address, labels, scan, credential: str, remediations: list[str]), and `Inventory` (groups: dict[str, InventoryGroup], targets: dict[str, Target])
- [x] 1.3 Add a `model_validator(mode="after")` on `Inventory` that merges each target's referenced `group` defaults into the target and raises a validation error if the target references an unknown group

## 2. Loader

- [x] 2.1 Create `yubarta/inventory/loader.py` with `load_inventory(path: str | Path) -> Inventory` that reads YAML via `yaml.safe_load` and validates it with `Inventory.model_validate`, letting `FileNotFoundError`, `yaml.YAMLError`, and `pydantic.ValidationError` propagate unchanged

## 3. Label Matching

- [x] 3.1 Create `yubarta/inventory/matcher.py` with `InventoryMatchError` (base), `NoMatchingTargetError`, and `AmbiguousTargetError(candidates: list[str])`
- [x] 3.2 Implement `match_target(inventory: Inventory, signal: Signal) -> Target` using subset-match semantics (target labels ⊆ signal labels); raise `NoMatchingTargetError` on zero matches and `AmbiguousTargetError` on more than one match

## 4. Dependency Wiring

- [x] 4.1 Create `yubarta/inventory/dependencies.py` with `get_inventory()` FastAPI dependency that loads the inventory once (singleton, same pattern as `yubarta/ingestion/dependencies.py`) from a path read via `Settings`
- [x] 4.2 Add `INVENTORY_PATH` to `yubarta/config/settings.py` (default `"inventory.yaml"`)

## 5. Dev Fixture

- [x] 5.1 Create a dev-fixture `inventory.yaml` at the repo root mirroring the spec's example (`java-app-1`, `redis-cache-1`), with a comment noting that target labels should be specific enough to avoid accidental subset-matches

## 6. Tests

- [x] 6.1 Create `tests/inventory/test_loader.py`: valid file loads and group defaults merge correctly; missing file raises `FileNotFoundError`; malformed YAML raises `yaml.YAMLError`; missing required field and unknown group reference each raise `ValidationError`
- [x] 6.2 Create `tests/inventory/test_matcher.py`: unique match returns the right target; zero matches raises `NoMatchingTargetError`; overlapping target label sets on one signal raises `AmbiguousTargetError` with both candidate names listed; extra signal labels beyond the target's don't block a match

## 7. Learning Note

- [x] 7.1 Write `dev-docs/learnings/target-inventory.md` covering: the subset-match decision vs. exact-equality, and anything surprising discovered during implementation
