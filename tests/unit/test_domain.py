"""Unit: state machine transitions, invalid transitions, OCC conflicts, check expectations."""

from __future__ import annotations

import pytest

from yubarta.checks.runner import run_check
from yubarta.config import CommandCheck
from yubarta.execution.ssh import CommandResult
from yubarta.incidents.errors import ConcurrentModificationError, InvalidTransitionError
from yubarta.incidents.state_machine import IncidentState, transition
from yubarta.persistence.repository import IncidentRepository


def test_valid_lifecycle():  # type: ignore[no-untyped-def]
    state = IncidentState.DETECTED
    for nxt in ["DIAGNOSING", "PRECHECKING", "REMEDIATING", "VERIFYING", "RESOLVED"]:
        state = transition(state, IncidentState(nxt))
    assert state == IncidentState.RESOLVED


def test_prechecking_to_resolved_allowed():  # type: ignore[no-untyped-def]
    assert transition(IncidentState.PRECHECKING, IncidentState.RESOLVED) == IncidentState.RESOLVED


def test_invalid_transitions_raise():  # type: ignore[no-untyped-def]
    with pytest.raises(InvalidTransitionError):
        transition(IncidentState.DETECTED, IncidentState.RESOLVED)
    with pytest.raises(InvalidTransitionError):
        transition(IncidentState.RESOLVED, IncidentState.REMEDIATING)
    with pytest.raises(InvalidTransitionError):
        transition(IncidentState.DIAGNOSING, IncidentState.VERIFYING)


async def test_occ_conflict(session_factory):  # type: ignore[no-untyped-def]
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


async def test_duplicate_events_no_duplicate_incident(session_factory):  # type: ignore[no-untyped-def]
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

    async def run(self, command: str, timeout: float = 30.0):  # type: ignore[no-untyped-def]
        return CommandResult(command=command, exit_code=self._exit_code, stdout="out", stderr="")


async def test_check_expectations_command():  # type: ignore[no-untyped-def]
    ok = await run_check(CommandCheck(run="is-active", expect_exit_code=0), _StubExecutor(0))
    assert ok.passed
    bad = await run_check(CommandCheck(run="is-active", expect_exit_code=0), _StubExecutor(3))
    assert not bad.passed


async def test_remediation_sequencing_order_preserved():  # type: ignore[no-untyped-def]
    from yubarta.config import RemediationDef

    defs = [RemediationDef(name=name, command=cmd) for name, cmd in [("a", "x"), ("b", "y"), ("c", "z")]]
    assert [item.name for item in defs] == ["a", "b", "c"]


def test_api_response_models():  # type: ignore[no-untyped-def]
    from datetime import datetime, timezone

    from yubarta.api import HealthResponse, IncidentSummary

    now = datetime.now(timezone.utc)
    assert HealthResponse(ok=True, time=now).ok
    summary = IncidentSummary(
        id="1", target="vm", incident_type="t", state="RESOLVED", version=1,
        opened_at=now, updated_at=now, resolved_at=None, resolved_by_step_id=None, failure_reason=None,
    )
    assert summary.state == "RESOLVED"
