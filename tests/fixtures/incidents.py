from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from types import TracebackType
from typing import Self

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from yubarta.config.settings import AppConfig, HttpCheck
from yubarta.controllers.checks import ChecksRunner
from yubarta.controllers.diagnostics import DiagnosticsRunner
from yubarta.controllers.incidents import IncidentService
from yubarta.controllers.remediations.runner import RemediationRunner
from yubarta.core.models import CheckOutcome, CommandResult
from yubarta.core.rules import RuleEngine
from yubarta.drivers.db.sqlalchemy import SqlAlchemyUnitOfWork


@dataclass
class Target:
    healthy: bool = False
    active_transactions: int = 0
    commands: list[str] = field(default_factory=list)

    async def run(self, command: str, timeout: float = 60.0) -> CommandResult:
        assert self.active_transactions == 0, "External operation inside a unit of work"
        self.commands.append(command)
        if command == "timeout":
            raise TimeoutError("command timed out")
        if command == "restart":
            self.healthy = True
        exit_code = 1 if command == "fail" or (command == "probe" and not self.healthy) else 0
        return CommandResult(command, exit_code, "output", "")


class TrackedUnitOfWork(SqlAlchemyUnitOfWork):
    def __init__(self, sessions: async_sessionmaker[AsyncSession], target: Target) -> None:
        super().__init__(sessions)
        self._target = target

    async def __aenter__(self) -> Self:
        await super().__aenter__()
        self._target.active_transactions += 1
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None
    ) -> None:
        try:
            await super().__aexit__(exc_type, exc_value, traceback)
        finally:
            self._target.active_transactions -= 1


class NoHttpChecks:
    async def check(self, check: HttpCheck) -> CheckOutcome:
        raise AssertionError("This scenario uses command checks only")


@pytest.fixture
def incident_case(
    session_factory: async_sessionmaker[AsyncSession],
) -> Callable[[AppConfig, bool, bool], tuple[IncidentService, Target]]:
    def build(config: AppConfig, apply: bool, healthy: bool = False) -> tuple[IncidentService, Target]:
        target = Target(healthy=healthy)
        service = IncidentService(
            config,
            lambda: TrackedUnitOfWork(session_factory, target),
            RuleEngine.from_watches(config.watch),
            DiagnosticsRunner(target, config.diagnostics),
            ChecksRunner(config.checks, target, NoHttpChecks()),
            RemediationRunner(target, apply),
        )
        return service, target

    return build
