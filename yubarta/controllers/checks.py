from yubarta.config.settings import Check, CommandCheck
from yubarta.core.interfaces import CommandPort, HTTPPort
from yubarta.core.models import ExecutionResult


class Checks:
    def __init__(self, commands: CommandPort, http: HTTPPort):
        self.commands = commands
        self.http = http

    async def run(self, check: Check) -> ExecutionResult:
        if isinstance(check, CommandCheck):
            result = await self.commands.run(check.run, check.timeout)
            return result.model_copy(update={"passed": not result.error and result.exit_code == check.expect.exit_code,
                                             "details": {"expected_exit_code": check.expect.exit_code}})
        return await self.http.check(check)
