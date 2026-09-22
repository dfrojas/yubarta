from uuid import uuid4

import pytest
from sqlalchemy import text

from yubarta.core.enums import IncidentState, StepKind
from yubarta.core.errors import ConcurrentModificationError, InvalidTransitionError
from yubarta.core.models import ExecutionResult, NormalizedEvent
from yubarta.drivers.db.initialization import migrate
from yubarta.drivers.db.sessions import Database

pytestmark = pytest.mark.integration


async def test_migrations_occ_and_atomic_history(database: Database, database_url: str) -> None:
    await migrate(database_url)
    event = NormalizedEvent(source="test", target="host", raw="failure", message="failure")
    async with database.uow() as work:
        incident, created = await work.repository.record_event(event, "tomcat-unavailable")
    assert incident is not None and created
    async with database.uow() as work:
        changed = await work.repository.transition(incident, IncidentState.DIAGNOSING, "diagnose")
    assert changed.version == incident.version + 1
    with pytest.raises(ConcurrentModificationError):
        async with database.uow() as work:
            await work.repository.transition(incident, IncidentState.DIAGNOSING, "stale")
    with pytest.raises(InvalidTransitionError):
        async with database.uow() as work:
            await work.repository.transition(changed, IncidentState.RESOLVED, "invalid")
    async with database.uow() as work:
        detail = await work.repository.detail(incident.id)
        assert [transition.reason for transition in detail.transitions] == ["Matching scanner event", "diagnose"]
        duplicate, created = await work.repository.record_event(event, "tomcat-unavailable")
        assert duplicate is None and not created
        attached, created = await work.repository.record_event(event.model_copy(update={"raw": "second failure"}), "tomcat-unavailable")
        assert attached.id == incident.id and not created
        await work.repository.transition(changed, IncidentState.FAILED, "exhausted")
    async with database.uow() as work:
        later, created = await work.repository.record_event(event.model_copy(update={"raw": "future failure"}), "tomcat-unavailable")
        assert created and later.id != incident.id
        detail = await work.repository.detail(incident.id)
        assert len(detail.events) == 2


async def test_rollback_output_bounds_and_recovery_attribution(database: Database) -> None:
    event = NormalizedEvent(source="test", target="host", raw=str(uuid4()), message="failure")
    with pytest.raises(RuntimeError):
        async with database.uow() as work:
            await work.repository.record_event(event, "tomcat-unavailable")
            raise RuntimeError("rollback")
    async with database.uow() as work:
        assert await work.repository.list() == []
        incident, _ = await work.repository.record_event(event, "tomcat-unavailable")
        step = await work.repository.start_step(incident.id, StepKind.DIAGNOSTIC, "output")
        step = await work.repository.finish_step(step, ExecutionResult(stdout="x" * 20000, stderr="y" * 20000, passed=True))
        assert len(step.stdout) == len(step.stderr) == 8192
    async with database.engine.connect() as connection:
        assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == "0001"
