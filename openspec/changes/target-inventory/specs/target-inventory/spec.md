## ADDED Requirements

### Requirement: Inventory schema and loading
The system SHALL define a typed schema for `inventory.yaml` (`groups` and `targets`) and SHALL load and validate a file against that schema at startup, failing fast on missing file, malformed YAML, or schema violations.

#### Scenario: Valid inventory loads successfully
- **WHEN** `load_inventory` is called with a path to a well-formed `inventory.yaml` matching the schema
- **THEN** it returns an `Inventory` object containing all defined targets, each with its group defaults merged in

#### Scenario: Missing file fails fast
- **WHEN** `load_inventory` is called with a path that does not exist
- **THEN** it raises an error immediately rather than returning a partial or empty inventory

#### Scenario: Malformed YAML fails fast
- **WHEN** `load_inventory` is called with a file that is not valid YAML
- **THEN** it raises an error identifying the parse failure

#### Scenario: Schema violation fails fast
- **WHEN** an inventory file omits a required field (e.g. a target with no `address`) or references an undefined `group`
- **THEN** `load_inventory` raises a validation error naming the offending target and field, and no `Inventory` object is returned

### Requirement: Signal-to-target label matching
The system SHALL resolve which `Target` a `Signal` refers to by matching the signal's labels against each target's labels, where a target matches when all of its labels are present with equal values in the signal's labels.

#### Scenario: Unique match resolves the target
- **WHEN** exactly one target's labels are a subset of the signal's labels
- **THEN** `match_target` returns that target

#### Scenario: No matching target escalates
- **WHEN** no target's labels are a subset of the signal's labels
- **THEN** `match_target` raises a `NoMatchingTargetError` and does not select any target

#### Scenario: Ambiguous match escalates
- **WHEN** more than one target's labels are each a subset of the signal's labels
- **THEN** `match_target` raises an `AmbiguousTargetError` identifying all candidate target names, and does not select any of them

### Requirement: Credential and remediation references are passed through, not resolved
The system SHALL preserve each target's `credential` reference and `remediations` allowlist as opaque, unresolved data at this stage.

#### Scenario: Credential reference is not resolved
- **WHEN** an inventory is loaded with a target whose `credential` is `sops://secrets/hosts/x.yaml#ssh_key`
- **THEN** the loaded `Target.credential` equals that string unchanged, and no secret resolution is attempted

#### Scenario: Remediations allowlist is preserved
- **WHEN** an inventory is loaded with a target whose `remediations` lists one or more remediation names
- **THEN** the loaded `Target.remediations` contains exactly those names, unvalidated against any remediation registry
