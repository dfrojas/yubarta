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


class DuplicateAttemptError(IncidentStoreError):
    """Raised when a remediation attempt with the same idempotency key is already
    recorded but has no outcome yet, i.e. it may still be in flight. The caller
    must not re-execute the remediation.
    """

    def __init__(self, idempotency_key: str) -> None:
        super().__init__(f"attempt with idempotency key '{idempotency_key}' is already recorded and pending")
        self.idempotency_key = idempotency_key


class IncidentStoreConsistencyError(IncidentStoreError):
    """Raised if an incident cannot be read back immediately after an idempotent
    create, which would mean the row vanished between insert and read.
    """

    def __init__(self, signal_id: str) -> None:
        super().__init__(f"incident for signal '{signal_id}' could not be read back after create")
        self.signal_id = signal_id
