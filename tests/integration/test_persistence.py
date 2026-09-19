"""Integration: PostgreSQL-schema persistence via real SQLAlchemy, Alembic metadata, transitions."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from yubarta.events.models import NormalizedEvent
from yubarta.incidents.models import StepKind, StepState
from yubarta.incidents.state_machine import IncidentState
from yubarta.persistence.repository import IncidentRepository


async def test_full_persistence_lifecycle(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        repo = IncidentRepository(session)
        incident, created = await repo.get_or_create_active("vm1", "tomcat-unavailable")
        assert created
        event = NormalizedEvent(source="log:/x", target="vm1", message="AH00957 AJP", raw="raw")
        stored = await repo.add_trigger_event(incident.id, event)
        assert stored is not None
        assert await repo.add_trigger_event(incident.id, event) is None  # fingerprint dedup
        row = await repo.transition_state(incident.id, incident.version, IncidentState.DIAGNOSING, "d")
        step = await repo.add_step(row.id, StepKind.DIAGNOSTIC, "uptime")
        await repo.update_step(step.id, state=StepState.SUCCEEDED.value, exit_code=0, stdout_excerpt="ok")
        transitions = await repo.list_transitions(row.id)
        assert len(transitions) >= 2
        steps = await repo.list_steps(row.id)
        assert steps[0].name == "uptime"
        await session.commit()


async def test_stdout_truncation(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        repo = IncidentRepository(session)
        incident, _ = await repo.get_or_create_active("vm2", "tomcat-unavailable")
        step = await repo.add_step(incident.id, StepKind.DIAGNOSTIC, "big")
        updated = await repo.update_step(step.id, stdout_excerpt="x" * 9000)
        assert updated.stdout_excerpt is not None and len(updated.stdout_excerpt) < 9000
        await session.commit()
