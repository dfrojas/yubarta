"""Unit: dry-run never changes the target."""

from __future__ import annotations

from yubarta.config import AppConfig, CommandCheck, LogWatch, RemediationDef, TargetConfig, VerifyConfig
from yubarta.diagnostics.runner import DiagnosticsRunner
from yubarta.events.models import NormalizedEvent
from yubarta.incidents.service import IncidentService
from yubarta.persistence.repository import IncidentRepository
from yubarta.persistence.session import create_engine, create_session_factory, init_db
from yubarta.rules.engine import RuleEngine


class _RecordingExecutor:
    def __init__(self) -> None:
        self.commands: list[str] = []

    async def run(self, command: str, timeout: float = 60.0):  # type: ignore[no-untyped-def]
        from yubarta.execution.ssh import CommandResult

        self.commands.append(command)
        if "is-active" in command:
            return CommandResult(command=command, exit_code=3, stdout="inactive", stderr="")
        return CommandResult(command=command, exit_code=0, stdout="ok", stderr="")


async def test_dry_run_skips_remediations(test_db):  # type: ignore[no-untyped-def]
    recorder = _RecordingExecutor()

    url = test_db
    engine = create_engine(url)
    await init_db(engine)
    sessions = create_session_factory(engine)
    config = AppConfig(
        target=TargetConfig(host="vm", user="u", key=""),
        watch=[LogWatch(file="/x.log", match_any=["AH00957"])],
        diagnostics=["uptime"],
        checks=[CommandCheck(run="sudo -n systemctl is-active --quiet tomcat9", expect_exit_code=0)],
        remediations=[RemediationDef(name="restart-tomcat", command="sudo -n systemctl restart tomcat9")],
        verify=VerifyConfig(settle_delay=0.0, interval=0.01, timeout=0.2),
    )
    service = IncidentService(
        config,
        sessions,
        RuleEngine.from_watches(config.watch),
        recorder,
        DiagnosticsRunner(recorder, config.diagnostics),
        apply=False,
    )
    event = NormalizedEvent(source="log:/x.log", target="vm", message="AH00957 fail", raw="x")
    await service.handle_event(event)
    # remediation command must never execute in dry-run; only diagnostics + checks ran
    assert "sudo -n systemctl restart tomcat9" not in recorder.commands
    async with sessions() as session:
        repo = IncidentRepository(session)
        incidents = await repo.list_incidents()
        assert incidents
        steps = await repo.list_steps(incidents[0].id)
        remediation_steps = [step for step in steps if step.kind == "remediation"]
        assert remediation_steps and all(step.state == "SKIPPED" for step in remediation_steps)
    await engine.dispose()
