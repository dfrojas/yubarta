## ADDED Requirements

### Requirement: Incident creation from a matched Signal and Target
The system SHALL create exactly one `Incident` per distinct `(Signal.id, Target)` pair, in the `received` state, persisting the triggering `Signal` and the resolved target's name.

#### Scenario: New signal creates a new incident
- **WHEN** a `Signal` with a `Signal.id` not already associated with an open incident is matched to a `Target`
- **THEN** the store creates a new `Incident` in the `received` state referencing that `Signal` and target name

#### Scenario: Duplicate signal does not create a duplicate incident
- **WHEN** a `Signal` with the same `Signal.id` as an already-persisted incident is submitted again
- **THEN** the store does not create a second `Incident` for it

### Requirement: Incident lifecycle transitions are persisted atomically
The system SHALL persist every incident state transition as an append-only record, and SHALL update the incident's current-state field in the same transaction as that record, so the two can never disagree.

#### Scenario: Valid transition is recorded
- **WHEN** an incident in state `diagnosing` transitions to `remediating`
- **THEN** the store appends a transition record `diagnosing → remediating` and updates the incident's current state to `remediating`, both durably committed together

#### Scenario: Transition history reconstructs current state
- **WHEN** an incident's full transition history is read back
- **THEN** folding the transitions in order yields the same state as the incident's denormalized current-state field

#### Scenario: Concurrent transitions are serialized, not silently lost
- **WHEN** two writers (e.g. two Director replicas) attempt to transition the same incident at the same time
- **THEN** the store serializes them so one transition fully commits before the other reads and applies on top of it, rather than the two interleaving and one silently overwriting the other

### Requirement: Remediation attempts are recorded before execution
The system SHALL persist a `RemediationAttempt` record, including its idempotency key, before the remediation it describes is executed, and SHALL update that same record with the outcome once execution completes.

#### Scenario: Attempt is recorded pre-execution
- **WHEN** the orchestrator decides to run a remediation for an incident
- **THEN** the store persists a `RemediationAttempt` row with a deterministic idempotency key derived from the incident id, remediation name, and attempt sequence, before the remediation runs

#### Scenario: Idempotency key detects a repeated attempt after a crash
- **WHEN** a `RemediationAttempt` is looked up by its deterministic idempotency key and a matching row already exists with no recorded outcome
- **THEN** the caller can determine the remediation may already be in flight or have run, instead of blindly re-executing it

#### Scenario: Attempt outcome is recorded after execution
- **WHEN** a previously recorded `RemediationAttempt` completes
- **THEN** the store updates that same row with its outcome (`succeeded`, `failed`, or `skipped`) and completion timestamp

### Requirement: Per-attempt approval is auditable
The system SHALL record the approval status of each `RemediationAttempt` (`not_required`, `pending`, `approved`, `denied`) together with who approved it and when, so an approval-requiring execution has a durable audit trail. The system SHALL NOT store whether a remediation *requires* approval — that is a static property of the remediation definition, owned by the remediation registry.

#### Scenario: An attempt that requires no approval
- **WHEN** a `RemediationAttempt` is recorded for a remediation that requires no approval
- **THEN** its approval status is `not_required` and no approver is recorded

#### Scenario: An approval-requiring attempt is recorded pending before execution
- **WHEN** a `RemediationAttempt` is recorded for a remediation that requires approval
- **THEN** the store persists it with approval status `pending` before the remediation runs, and the approval decision (`approved` or `denied`, with the approver's identity and timestamp) can be recorded against that same row once it is made, independent of the channel the approval arrived through

### Requirement: Incident history is readable by id, by target, and as a recent list
The system SHALL expose read operations for a single incident by id, all incidents for a given target name, and the most recent N incidents, each including their remediation attempts.

#### Scenario: Read by id includes attempts
- **WHEN** an incident is read by its id
- **THEN** the result includes the incident's current state, its triggering signal, and the ordered list of its remediation attempts

#### Scenario: Read by target name returns only that target's incidents
- **WHEN** incidents are read for a given target name
- **THEN** the result includes only incidents whose `target_name` matches, ordered most-recent-first

#### Scenario: Recent incidents are bounded
- **WHEN** the most recent N incidents are requested
- **THEN** the result contains at most N incidents, ordered most-recent-first, regardless of total incident count in the store
