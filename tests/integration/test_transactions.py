import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from yubarta.core.enums import IncidentState, StepKind
from yubarta.core.errors import ConcurrentModificationError
from yubarta.core.models import Incident, NormalizedEvent
from yubarta.drivers.db.sqlalchemy import SqlAlchemyUnitOfWork


@pytest.mark.parametrize("failure", [None, ValueError, asyncio.CancelledError])
async def test_uncommitted_work_rolls_back(
    session_factory: async_sessionmaker[AsyncSession], failure: type[BaseException] | None
) -> None:
    async def write() -> None:
        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            incident, _ = await uow.incidents.get_or_create_active("vm", "unavailable")
            await uow.incidents.add_step(incident.id, StepKind.DIAGNOSTIC, "uptime")
            if failure is not None:
                raise failure()

    if failure is None:
        await write()
    else:
        with pytest.raises(failure):
            await write()
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        assert await uow.incidents.list_incidents() == []


async def test_commit_returns_detached_domain_models(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        incident, _ = await uow.incidents.get_or_create_active("vm", "unavailable")
        await uow.incidents.add_trigger_event(
            incident.id, NormalizedEvent(source="test", target="vm", message="failure", raw="failure")
        )
        await uow.commit()
    assert isinstance(incident, Incident)
    assert incident.target == "vm"
    # Mutating the returned model must not bypass the repository or audit trail.
    incident.failure_reason = "not persisted"
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        stored = await uow.incidents.get(incident.id)
        assert stored is not None and stored.failure_reason is None
        assert len(await uow.incidents.list_trigger_events(incident.id)) == 1
        assert len(await uow.incidents.list_transitions(incident.id)) == 1


async def test_stale_write_rolls_back_its_steps_and_history(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        original, _ = await uow.incidents.get_or_create_active("vm", "unavailable")
        await uow.commit()
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.incidents.transition_state(original.id, original.version, IncidentState.DIAGNOSING)
        await uow.commit()
    with pytest.raises(ConcurrentModificationError):
        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            await uow.incidents.add_step(original.id, StepKind.PRECHECK, "stale check")
            await uow.incidents.transition_state(original.id, original.version, IncidentState.PRECHECKING)
            await uow.commit()
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        incident = await uow.incidents.get(original.id)
        assert incident is not None and incident.state == IncidentState.DIAGNOSING
        assert incident.version == 1
        assert await uow.incidents.list_steps(original.id) == []
        assert len(await uow.incidents.list_transitions(original.id)) == 2
