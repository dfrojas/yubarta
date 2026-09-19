"""Repository: incident lifecycle persistence with OCC and audit history."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from yubarta.core.enums import IncidentState, StepKind, StepState
from yubarta.core.errors import ConcurrentModificationError
from yubarta.core.models import Incident, IncidentStep, NormalizedEvent, StateTransition, TriggerEvent
from yubarta.core.state_machine import transition
from yubarta.drivers.db.orm import (
    IncidentRow,
    IncidentStateTransitionRow,
    IncidentStepRow,
    TriggerEventRow,
)

MAX_EXCERPT = 4000


def _excerpt(text: str | None, limit: int = MAX_EXCERPT) -> str | None:
    if text is None:
        return None
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... [truncated {len(text) - limit} chars]"


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _new_id() -> str:
    return uuid.uuid4().hex[:16]


class SqlAlchemyIncidentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_active(self, target: str, incident_type: str) -> Incident | None:
        result = await self._session.execute(
            select(IncidentRow).where(
                IncidentRow.target == target,
                IncidentRow.incident_type == incident_type,
                IncidentRow.state.notin_(["RESOLVED", "FAILED"]),
            )
        )
        row = result.scalars().first()
        return Incident.model_validate(row, from_attributes=True) if row is not None else None

    async def get(self, incident_id: str) -> Incident | None:
        row = await self._session.get(IncidentRow, incident_id)
        return Incident.model_validate(row, from_attributes=True) if row is not None else None

    async def create(self, target: str, incident_type: str) -> Incident:
        now = _utcnow()
        row = IncidentRow(
            id=_new_id(),
            target=target,
            incident_type=incident_type,
            state=IncidentState.DETECTED.value,
            version=0,
            opened_at=now,
            updated_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        await self._record_transition(row.id, None, IncidentState.DETECTED.value, "incident detected")
        return Incident.model_validate(row, from_attributes=True)

    async def get_or_create_active(self, target: str, incident_type: str) -> tuple[Incident, bool]:
        existing = await self.find_active(target, incident_type)
        if existing is not None:
            return existing, False
        return await self.create(target, incident_type), True

    async def _record_transition(self, incident_id: str, from_state: str | None, to_state: str, reason: str) -> None:
        self._session.add(
            IncidentStateTransitionRow(
                id=_new_id(),
                incident_id=incident_id,
                from_state=from_state or "",
                to_state=to_state,
                created_at=_utcnow(),
                reason=reason,
            )
        )

    async def transition_state(
        self, incident_id: str, expected_version: int, to_state: IncidentState, reason: str = ""
    ) -> Incident:
        row = await self._session.get(IncidentRow, incident_id)
        if row is None:
            raise ValueError(f"Incident not found: {incident_id}")
        from_state = IncidentState(row.state)
        transition(from_state, to_state)
        result = await self._session.execute(
            update(IncidentRow)
            .where(IncidentRow.id == incident_id, IncidentRow.version == expected_version)
            .values(state=to_state.value, version=IncidentRow.version + 1, updated_at=_utcnow())
        )
        if result.rowcount == 0:
            raise ConcurrentModificationError(f"OCC conflict on incident {incident_id}")
        await self._record_transition(incident_id, from_state.value, to_state.value, reason)
        await self._session.flush()
        updated = await self._session.get(IncidentRow, incident_id)
        assert updated is not None
        return Incident.model_validate(updated, from_attributes=True)

    async def mark_resolved(
        self,
        incident_id: str,
        expected_version: int,
        resolved_by_step_id: str | None,
        reason: str = "",
    ) -> Incident:
        await self.transition_state(incident_id, expected_version, IncidentState.RESOLVED, reason)
        row = await self._session.get(IncidentRow, incident_id)
        assert row is not None
        row.resolved_at = _utcnow()
        row.resolved_by_step_id = resolved_by_step_id
        await self._session.flush()
        return Incident.model_validate(row, from_attributes=True)

    async def mark_failed(self, incident_id: str, expected_version: int, reason: str) -> Incident:
        await self.transition_state(incident_id, expected_version, IncidentState.FAILED, reason)
        row = await self._session.get(IncidentRow, incident_id)
        assert row is not None
        row.failure_reason = reason
        await self._session.flush()
        return Incident.model_validate(row, from_attributes=True)

    async def add_trigger_event(self, incident_id: str, event: NormalizedEvent) -> TriggerEvent | None:
        fingerprint = event.fingerprint()
        existing = await self._session.execute(
            select(TriggerEventRow).where(
                TriggerEventRow.incident_id == incident_id,
                TriggerEventRow.fingerprint == fingerprint,
            )
        )
        if existing.scalars().first() is not None:
            return None
        row = TriggerEventRow(
            id=_new_id(),
            incident_id=incident_id,
            source=event.source,
            fingerprint=fingerprint,
            observed_at=event.observed_at,
            raw=event.raw[:MAX_EXCERPT],
            fields={"message": event.message, **event.fields},
        )
        self._session.add(row)
        await self._session.flush()
        return TriggerEvent.model_validate(row, from_attributes=True)

    async def next_sequence(self, incident_id: str) -> int:
        result = await self._session.execute(select(IncidentStepRow).where(IncidentStepRow.incident_id == incident_id))
        return len(result.scalars().all()) + 1

    async def add_step(
        self,
        incident_id: str,
        kind: StepKind,
        name: str,
        state: StepState = StepState.PENDING,
    ) -> IncidentStep:
        sequence = await self.next_sequence(incident_id)
        row = IncidentStepRow(
            id=_new_id(),
            incident_id=incident_id,
            sequence=sequence,
            kind=kind.value,
            name=name,
            state=state.value,
        )
        self._session.add(row)
        await self._session.flush()
        return IncidentStep.model_validate(row, from_attributes=True)

    async def update_step(self, step_id: str, **fields: object) -> IncidentStep:
        row = await self._session.get(IncidentStepRow, step_id)
        if row is None:
            raise ValueError(f"Step not found: {step_id}")
        if "stdout_excerpt" in fields and isinstance(fields["stdout_excerpt"], str):
            fields["stdout_excerpt"] = _excerpt(fields["stdout_excerpt"])
        if "stderr_excerpt" in fields and isinstance(fields["stderr_excerpt"], str):
            fields["stderr_excerpt"] = _excerpt(fields["stderr_excerpt"])
        for key, value in fields.items():
            setattr(row, key, value)
        await self._session.flush()
        return IncidentStep.model_validate(row, from_attributes=True)

    async def list_steps(self, incident_id: str) -> list[IncidentStep]:
        result = await self._session.execute(
            select(IncidentStepRow).where(IncidentStepRow.incident_id == incident_id).order_by(IncidentStepRow.sequence)
        )
        return [IncidentStep.model_validate(row, from_attributes=True) for row in result.scalars()]

    async def list_transitions(self, incident_id: str) -> list[StateTransition]:
        result = await self._session.execute(
            select(IncidentStateTransitionRow)
            .where(IncidentStateTransitionRow.incident_id == incident_id)
            .order_by(IncidentStateTransitionRow.created_at)
        )
        return [StateTransition.model_validate(row, from_attributes=True) for row in result.scalars()]

    async def list_trigger_events(self, incident_id: str) -> list[TriggerEvent]:
        result = await self._session.execute(select(TriggerEventRow).where(TriggerEventRow.incident_id == incident_id))
        return [TriggerEvent.model_validate(row, from_attributes=True) for row in result.scalars()]

    async def list_incidents(self, limit: int = 50) -> list[Incident]:
        result = await self._session.execute(select(IncidentRow).order_by(IncidentRow.opened_at.desc()).limit(limit))
        return [Incident.model_validate(row, from_attributes=True) for row in result.scalars()]
