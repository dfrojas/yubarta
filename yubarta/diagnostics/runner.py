"""Diagnostics runner: best-effort evidence collection after detection."""

from __future__ import annotations

from datetime import datetime, timezone

from yubarta.execution.ssh import CommandResult, SSHConnectionFactory
from yubarta.incidents.models import StepKind


class DiagnosticResult:
    def __init__(self, name: str, exit_code: int, stdout: str, stderr: str, ok: bool) -> None:
        self.name = name
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.ok = ok


class DiagnosticsRunner:
    def __init__(self, executor: SSHConnectionFactory, commands: list[str]) -> None:
        self._executor = executor
        self._commands = commands

    async def run_all(self) -> list[DiagnosticResult]:
        results: list[DiagnosticResult] = []
        for command in self._commands:
            try:
                outcome: CommandResult = await self._executor.run(command, timeout=60.0)
                results.append(
                    DiagnosticResult(command, outcome.exit_code, outcome.stdout, outcome.stderr, True)
                )
            except Exception as exc:  # best-effort: record and continue
                results.append(DiagnosticResult(command, 1, "", str(exc), False))
        return results

    @staticmethod
    def kind() -> StepKind:
        return StepKind.DIAGNOSTIC

    @staticmethod
    def now() -> datetime:
        return datetime.now(timezone.utc)
