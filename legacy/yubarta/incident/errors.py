from yubarta.incident.models import RemediationAttempt


class IncidentStoreError(Exception):
    """Base class for incident-store errors."""


class IncidentNotFoundError(IncidentStoreError):
    def __init__(self, incident_id: str) -> None:
        super().__init__(f"incident '{incident_id}' does not exist")
        self.incident_id = incident_id


class AttemptNotFoundError(IncidentStoreError):
    def __init__(self, attempt_id: str) -> None:
        super().__init__(f"remediation attempt '{attempt_id}' does not exist")
        self.attempt_id = attempt_id


class ConcurrentModificationError(IncidentStoreError):
    """Raised when a transition's expected version does not match the persisted
    one, meaning another writer moved the incident after this caller read it.

    The caller must re-read and re-decide, never blindly retry: its decision was
    computed from state that no longer holds (ADR-0006).
    """

    def __init__(self, incident_id: str, expected_version: int, persisted_version: int) -> None:
        super().__init__(
            f"incident '{incident_id}' moved from version {expected_version} to {persisted_version} "
            "before this transition was applied"
        )
        self.incident_id = incident_id
        self.expected_version = expected_version
        self.persisted_version = persisted_version


class StaleLeaseError(IncidentStoreError):
    """Raised when a state-changing write carries a lease generation that does not
    match the persisted one, meaning ownership changed under the caller.

    Distinct from `ConcurrentModificationError` on purpose: this rejection happens
    even when the expected version matches, because a replica whose lease was
    superseded has no right to act regardless of how current its view of the state
    is (ADR-0006).
    """

    def __init__(self, incident_id: str, submitted_generation: int, persisted_generation: int) -> None:
        super().__init__(
            f"incident '{incident_id}' is at lease generation {persisted_generation}, "
            f"write carried generation {submitted_generation}"
        )
        self.incident_id = incident_id
        self.submitted_generation = submitted_generation
        self.persisted_generation = persisted_generation


class DuplicateAttemptError(IncidentStoreError):
    """Raised when a remediation attempt with the same idempotency key is already
    recorded. The caller must not re-execute the remediation.

    Carries the existing attempt so the caller can tell the two cases apart:
    no recorded outcome means the attempt may still be in flight and the side
    effect may or may not have happened, while a recorded outcome means it
    finished and the result is readable instead of re-runnable.
    """

    def __init__(self, idempotency_key: str, existing_attempt: RemediationAttempt) -> None:
        progress = "already completed" if existing_attempt.outcome is not None else "still in flight"
        super().__init__(f"attempt with idempotency key '{idempotency_key}' is {progress}")
        self.idempotency_key = idempotency_key
        self.existing_attempt = existing_attempt


class IncidentStoreConsistencyError(IncidentStoreError):
    """Raised if an incident cannot be read back immediately after an idempotent
    create, which would mean the row vanished between insert and read.
    """

    def __init__(self, signal_id: str) -> None:
        super().__init__(f"incident for signal '{signal_id}' could not be read back after create")
        self.signal_id = signal_id
