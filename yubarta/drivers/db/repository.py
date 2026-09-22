from uuid import UUID, uuid4

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from yubarta.core.enums import IncidentState, StepKind, StepState
from yubarta.core.errors import ConcurrentModificationError
from yubarta.core.models import ExecutionResult, Incident, IncidentDetail, NormalizedEvent, Step, Transition, Trigger, utcnow
from yubarta.core.state_machine import validate_transition
from yubarta.drivers.db.orm import IncidentRow, StepRow, TransitionRow, TriggerRow


class Repository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, incident_id: UUID) -> Incident | None:
        row = await self.session.get(IncidentRow, incident_id)
        return Incident.model_validate(row) if row else None

    async def list(self, limit: int = 100, active: bool = False) -> list[Incident]:
        query = select(IncidentRow).order_by(IncidentRow.opened_at.desc()).limit(limit)
        if active:
            query = query.where(IncidentRow.state.not_in(["RESOLVED", "FAILED"]))
        return [Incident.model_validate(row) for row in await self.session.scalars(query)]

    async def active_count(self) -> int:
        return await self.session.scalar(select(func.count()).select_from(IncidentRow).where(IncidentRow.state.not_in(["RESOLVED", "FAILED"]))) or 0

    async def record_event(self, event: NormalizedEvent, incident_type: str) -> tuple[Incident | None, bool]:
        fingerprint = event.fingerprint()
        if await self.session.scalar(select(TriggerRow.id).where(TriggerRow.fingerprint == fingerprint)):
            return None, False
        row = await self.session.scalar(select(IncidentRow).where(
            IncidentRow.target == event.target,
            IncidentRow.incident_type == incident_type,
            IncidentRow.state.not_in(["RESOLVED", "FAILED"]),
        ))
        created = row is None
        if row is None:
            now = utcnow()
            row = IncidentRow(id=uuid4(), target=event.target, incident_type=incident_type,
                              state=IncidentState.DETECTED, version=1, opened_at=now, updated_at=now)
            self.session.add(row)
            await self.session.flush()
            self.session.add(TransitionRow(incident_id=row.id, from_state=None, to_state=IncidentState.DETECTED,
                                           timestamp=now, reason="Matching scanner event"))
        self.session.add(TriggerRow(incident_id=row.id, source=event.source, fingerprint=fingerprint,
                                   observed_at=event.observed_at, raw=event.raw, normalized=event.model_dump(mode="json")))
        await self.session.flush()
        return Incident.model_validate(row), created

    async def transition(self, incident: Incident, destination: IncidentState, reason: str,
                         resolved_by: UUID | None = None) -> Incident:
        validate_transition(incident.state, destination)
        now = utcnow()
        values = {"state": destination, "version": incident.version + 1, "updated_at": now}
        if destination == IncidentState.RESOLVED:
            if resolved_by:
                step = await self.session.get(StepRow, resolved_by)
                if not step or step.incident_id != incident.id or step.kind != StepKind.REMEDIATION or step.state == StepState.SKIPPED:
                    raise ValueError("Resolution must reference this incident's executed remediation")
            values.update(resolved_at=now, resolved_by_step_id=resolved_by)
        if destination == IncidentState.FAILED:
            values["failure_reason"] = reason
        result = await self.session.execute(update(IncidentRow).where(
            IncidentRow.id == incident.id, IncidentRow.version == incident.version,
        ).values(**values).execution_options(synchronize_session=False))
        if result.rowcount != 1:
            raise ConcurrentModificationError(f"Incident {incident.id} version {incident.version} is stale")
        self.session.add(TransitionRow(incident_id=incident.id, from_state=incident.state,
                                       to_state=destination, timestamp=now, reason=reason))
        await self.session.flush()
        return incident.model_copy(update=values)

    async def start_step(self, incident_id: UUID, kind: StepKind, name: str) -> Step:
        sequence = (await self.session.scalar(select(func.max(StepRow.sequence)).where(StepRow.incident_id == incident_id)) or 0) + 1
        row = StepRow(id=uuid4(), incident_id=incident_id, sequence=sequence, kind=kind, name=name,
                      state=StepState.RUNNING, started_at=utcnow(), stdout="", stderr="", result={})
        self.session.add(row)
        await self.session.flush()
        return Step.model_validate(row)

    async def finish_step(self, step: Step, result: ExecutionResult, skipped: bool = False) -> Step:
        state = StepState.SKIPPED if skipped else StepState.TIMED_OUT if result.timed_out else StepState.SUCCEEDED if result.passed else StepState.FAILED
        values = dict(state=state, finished_at=utcnow(), exit_code=result.exit_code,
                      stdout=result.stdout[:8192], stderr=result.stderr[:8192], error=result.error,
                      result=result.model_dump(mode="json", exclude={"stdout", "stderr"}))
        await self.session.execute(update(StepRow).where(StepRow.id == step.id).values(**values))
        return step.model_copy(update=values)

    async def interrupt_steps(self, incident_id: UUID, reason: str) -> None:
        await self.session.execute(update(StepRow).where(
            StepRow.incident_id == incident_id, StepRow.state.in_([StepState.PENDING, StepState.RUNNING]),
        ).values(state=StepState.FAILED, finished_at=utcnow(), error=reason))

    async def detail(self, incident_id: UUID) -> IncidentDetail | None:
        incident = await self.get(incident_id)
        if incident is None:
            return None
        steps = await self.session.scalars(select(StepRow).where(StepRow.incident_id == incident_id).order_by(StepRow.sequence))
        transitions = await self.session.scalars(select(TransitionRow).where(TransitionRow.incident_id == incident_id).order_by(TransitionRow.id))
        events = await self.session.scalars(select(TriggerRow).where(TriggerRow.incident_id == incident_id).order_by(TriggerRow.id))
        return IncidentDetail(**incident.model_dump(), steps=[Step.model_validate(row) for row in steps],
                              transitions=[Transition.model_validate(row) for row in transitions],
                              events=[Trigger.model_validate(row) for row in events])
