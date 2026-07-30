from typing import Any, Protocol

from yubarta.domain.signal import Signal
from yubarta.incident.models import (
    AttemptApproval,
    AttemptOutcome,
    Incident,
    IncidentState,
    IncidentTransition,
    RemediationAttempt,
)


class IncidentStore(Protocol):
    async def create(self, signal: Signal, target_name: str) -> Incident: ...

    async def transition(
        self,
        incident_id: str,
        to_state: IncidentState,
        expected_version: int,
        lease_generation: int,
    ) -> Incident:
        """Apply a state change, guarded by two independent mechanisms (ADR-0006).

        `expected_version` rejects a write whose view of the state is stale.
        `lease_generation` rejects a write from a superseded owner, which a matching
        version cannot detect. Neither substitutes for the other, and neither
        prevents a remediation from executing twice: that is the pre-execution
        idempotency key on `record_attempt`.
        """
        ...

    async def record_attempt(
        self,
        incident_id: str,
        remediation_name: str,
        approval_status: AttemptApproval = AttemptApproval.not_required,
    ) -> RemediationAttempt: ...

    async def resolve_approval(
        self,
        attempt_id: str,
        approval_status: AttemptApproval,
        approved_by: str | None,
    ) -> RemediationAttempt: ...

    async def complete_attempt(
        self,
        attempt_id: str,
        outcome: AttemptOutcome,
        evidence: dict[str, Any] | None,
    ) -> RemediationAttempt: ...

    async def get(self, incident_id: str) -> Incident | None: ...

    async def list_transitions(self, incident_id: str) -> list[IncidentTransition]: ...

    async def list_by_target(self, target_name: str) -> list[Incident]: ...

    async def list_recent(self, limit: int) -> list[Incident]: ...


class MessageBus(Protocol):
    async def publish(self, topic: str, signal: Signal) -> None: ...


class RemoteExecutor(Protocol):
    async def exec(self, host: str, command: str) -> tuple[int, str, str]: ...
