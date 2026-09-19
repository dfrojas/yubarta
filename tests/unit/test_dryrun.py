"""Unit: dry-run never changes the target."""

from __future__ import annotations

from functools import partial

import httpx

from yubarta.config.settings import (
    AppConfig,
    CommandCheck,
    LogWatch,
    RemediationDef,
    TargetConfig,
    VerifyConfig,
)
from yubarta.controllers.checks import ChecksRunner
from yubarta.controllers.diagnostics import DiagnosticsRunner
from yubarta.controllers.incidents import IncidentService
from yubarta.controllers.remediations.runner import RemediationRunner
from yubarta.core.models import CommandResult, NormalizedEvent
from yubarta.core.rules import RuleEngine
from yubarta.drivers.db.initialization import init_db
from yubarta.drivers.db.repository import SqlAlchemyIncidentRepository as IncidentRepository
from yubarta.drivers.db.sessions import create_engine, create_session_factory
from yubarta.drivers.db.sqlalchemy import SqlAlchemyUnitOfWork
from yubarta.drivers.network.http import HttpChecks


class _RecordingExecutor:
    def __init__(self) -> None:
        self.commands: list[str] = []

    async def run(self, command: str, timeout: float = 60.0) -> CommandResult:
        self.commands.append(command)
        if "is-active" in command:
            return CommandResult(command=command, exit_code=3, stdout="inactive", stderr="")
        return CommandResult(command=command, exit_code=0, stdout="ok", stderr="")


async def test_dry_run_skips_remediations(test_db: str) -> None:
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
    http_client = httpx.AsyncClient()
    service = IncidentService(
        config,
        partial(SqlAlchemyUnitOfWork, sessions),
        RuleEngine.from_watches(config.watch),
        DiagnosticsRunner(recorder, config.diagnostics),
        ChecksRunner(config.checks, recorder, HttpChecks(http_client)),
        RemediationRunner(recorder, apply=False),
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
    await http_client.aclose()
