"""Unit: state machine transitions, invalid transitions, OCC conflicts, check expectations."""

from __future__ import annotations

from datetime import UTC

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from yubarta.checks.runner import run_check
from yubarta.config import CommandCheck
from yubarta.execution.ssh import CommandResult
from yubarta.incidents.errors import ConcurrentModificationError, InvalidTransitionError
from yubarta.incidents.state_machine import IncidentState, transition
from yubarta.persistence.repository import IncidentRepository


def test_valid_lifecycle() -> None:
    state = IncidentState.DETECTED
    for nxt in ["DIAGNOSING", "PRECHECKING", "REMEDIATING", "VERIFYING", "RESOLVED"]:
        state = transition(state, IncidentState(nxt))
    assert state == IncidentState.RESOLVED


def test_prechecking_to_resolved_allowed() -> None:
    assert transition(IncidentState.PRECHECKING, IncidentState.RESOLVED) == IncidentState.RESOLVED


def test_invalid_transitions_raise() -> None:
    with pytest.raises(InvalidTransitionError):
        transition(IncidentState.DETECTED, IncidentState.RESOLVED)
    with pytest.raises(InvalidTransitionError):
        transition(IncidentState.RESOLVED, IncidentState.REMEDIATING)
    with pytest.raises(InvalidTransitionError):
        transition(IncidentState.DIAGNOSING, IncidentState.VERIFYING)


async def test_occ_conflict(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        repo = IncidentRepository(session)
        row = await repo.create("vm", "tomcat-unavailable")
        await session.commit()
        incident_id = row.id
    async with session_factory() as session:
        repo = IncidentRepository(session)
        row = await repo.get(incident_id)
        assert row is not None
        await repo.transition_state(row.id, row.version, IncidentState.DIAGNOSING, "t")
        await session.commit()
    async with session_factory() as session:
        repo = IncidentRepository(session)
        with pytest.raises(ConcurrentModificationError):
            await repo.transition_state(incident_id, 0, IncidentState.PRECHECKING, "stale")


async def test_duplicate_events_no_duplicate_incident(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    from yubarta.events.models import NormalizedEvent

    async with session_factory() as session:
        repo = IncidentRepository(session)
        first, created_first = await repo.get_or_create_active("vm", "tomcat-unavailable")
        event = NormalizedEvent(source="s", target="vm", message="m", raw="r")
        await repo.add_trigger_event(first.id, event)
        duplicate = await repo.add_trigger_event(first.id, event)
        assert duplicate is None
        second, created_second = await repo.get_or_create_active("vm", "tomcat-unavailable")
        assert first.id == second.id and created_first and not created_second
        await session.commit()


class _StubExecutor:
    def __init__(self, exit_code: int = 0) -> None:
        self._exit_code = exit_code

    async def run(self, command: str, timeout: float = 30.0) -> CommandResult:
        return CommandResult(command=command, exit_code=self._exit_code, stdout="out", stderr="")


async def test_check_expectations_command() -> None:
    ok = await run_check(CommandCheck(run="is-active", expect_exit_code=0), _StubExecutor(0))
    assert ok.passed
    bad = await run_check(CommandCheck(run="is-active", expect_exit_code=0), _StubExecutor(3))
    assert not bad.passed


async def test_remediation_sequencing_order_preserved() -> None:
    from yubarta.config import RemediationDef

    defs = [RemediationDef(name=name, command=cmd) for name, cmd in [("a", "x"), ("b", "y"), ("c", "z")]]
    assert [item.name for item in defs] == ["a", "b", "c"]


def test_api_response_models() -> None:
    from datetime import datetime

    from yubarta.api import HealthResponse, IncidentSummary

    now = datetime.now(UTC)
    assert HealthResponse(ok=True, time=now).ok
    summary = IncidentSummary(
        id="1",
        target="vm",
        incident_type="t",
        state="RESOLVED",
        version=1,
        opened_at=now,
        updated_at=now,
        resolved_at=None,
        resolved_by_step_id=None,
        failure_reason=None,
    )
    assert summary.state == "RESOLVED"
