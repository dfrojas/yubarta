from unittest.mock import AsyncMock

from yubarta.config.settings import CommandCheck, CommandExpectation, Remediation
from yubarta.controllers.checks import Checks
from yubarta.controllers.remediations.runner import Remediations
from yubarta.core.models import ExecutionResult


async def test_dryrun_cannot_execute_and_checks_use_expectations() -> None:
    commands = AsyncMock()
    runner = Remediations(commands, apply=False)
    result = await runner.run(Remediation(name="restart", command="restart"))
    assert result.details == {"planned": True}
    commands.run.assert_not_called()
    commands.run.return_value = ExecutionResult(exit_code=3, stdout="failed")
    checks = Checks(commands, AsyncMock())
    assert (await checks.run(CommandCheck(run="check", expect=CommandExpectation(exit_code=3)))).passed
    assert not (await checks.run(CommandCheck(run="check"))).passed
