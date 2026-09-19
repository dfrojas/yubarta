from dataclasses import dataclass

from yubarta.config.settings import RemediationDef
from yubarta.core.enums import StepState
from yubarta.core.interfaces import CommandExecutor
from yubarta.core.models import CommandResult


@dataclass(frozen=True)
class RemediationOutcome:
    state: StepState
    result: CommandResult | None = None
    error: str | None = None


class RemediationRunner:
    def __init__(self, executor: CommandExecutor, apply: bool = False) -> None:
        self._executor = executor
        self._apply = apply

    @property
    def apply(self) -> bool:
        return self._apply

    async def run(self, remediation: RemediationDef) -> RemediationOutcome:
        if not self._apply:
            return RemediationOutcome(StepState.SKIPPED, error="dry-run: remediation skipped")
        try:
            result = await self._executor.run(remediation.command, timeout=300.0)
        except (ConnectionError, TimeoutError, OSError) as exc:
            return RemediationOutcome(StepState.FAILED, error=str(exc))
        if result.exit_code != 0:
            return RemediationOutcome(StepState.FAILED, result, f"exit={result.exit_code}")
        return RemediationOutcome(StepState.SUCCEEDED, result)
