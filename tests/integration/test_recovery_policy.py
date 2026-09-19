from collections.abc import Callable

import pytest

from tests.fixtures.incidents import Target
from yubarta.config.settings import AppConfig, CommandCheck, LogWatch, RemediationDef, TargetConfig, VerifyConfig
from yubarta.controllers.incidents import IncidentService
from yubarta.core.enums import IncidentState, StepKind, StepState
from yubarta.core.models import NormalizedEvent


@pytest.mark.parametrize(
    ("commands", "apply", "healthy", "expected", "step_states"),
    [
        (["restart"], True, True, IncidentState.RESOLVED, []),
        (["restart"], False, False, IncidentState.FAILED, [StepState.SKIPPED]),
        (["fail", "restart"], True, False, IncidentState.RESOLVED, [StepState.FAILED, StepState.SUCCEEDED]),
        (["timeout", "restart"], True, False, IncidentState.RESOLVED, [StepState.FAILED, StepState.SUCCEEDED]),
        (["no-effect", "restart"], True, False, IncidentState.RESOLVED, [StepState.SUCCEEDED, StepState.SUCCEEDED]),
        (["fail"], True, False, IncidentState.FAILED, [StepState.FAILED]),
        (["no-effect"], True, False, IncidentState.FAILED, [StepState.SUCCEEDED]),
        ([], False, False, IncidentState.FAILED, []),
        ([], True, False, IncidentState.FAILED, []),
    ],
)
async def test_recovery_preserves_policy_and_transaction_boundaries(
    incident_case: Callable[[AppConfig, bool, bool], tuple[IncidentService, Target]],
    commands: list[str],
    apply: bool,
    healthy: bool,
    expected: IncidentState,
    step_states: list[StepState],
) -> None:
    config = AppConfig(
        target=TargetConfig(host="vm", user="operator"),
        watch=[LogWatch(file="/app.log", match_any=["failure"])],
        diagnostics=["uptime"],
        checks=[CommandCheck(run="probe")],
        remediations=[RemediationDef(name=command, command=command) for command in commands],
        verify=VerifyConfig(settle_delay=0, interval=0.01, timeout=0),
    )
    service, target = incident_case(config, apply, healthy)
    ignored = NormalizedEvent(source="log:/app.log", target="vm", message="healthy", raw="healthy")
    assert await service.handle_event(ignored) is None
    assert target.commands == []

    incident_id = await service.handle_event(
        NormalizedEvent(source="log:/app.log", target="vm", message="failure", raw="failure")
    )
    assert incident_id is not None
    detail = await service.get_incident(incident_id)
    assert detail is not None and detail.incident.state == expected
    steps = [step for step in detail.steps if step.kind == StepKind.REMEDIATION]
    assert [step.state for step in steps] == step_states
    assert target.active_transactions == 0
    if healthy:
        assert target.commands == ["uptime", "probe"]
        assert detail.incident.resolved_by_step_id is None
    elif not apply:
        assert target.commands == ["uptime", "probe"]
        assert detail.incident.failure_reason == "dry-run: remediations skipped"
        assert all(step.stdout_excerpt is None for step in steps)
    elif expected == IncidentState.RESOLVED:
        assert detail.incident.resolved_by_step_id == steps[-1].id
        assert detail.incident.resolved_at is not None
    else:
        assert detail.incident.failure_reason
