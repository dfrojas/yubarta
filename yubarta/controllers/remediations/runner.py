from yubarta.config.settings import Remediation
from yubarta.core.interfaces import CommandPort
from yubarta.core.models import ExecutionResult


class Remediations:
    def __init__(self, commands: CommandPort, apply: bool):
        self.commands = commands
        self.apply = apply

    async def run(self, remediation: Remediation) -> ExecutionResult:
        if not self.apply:
            return ExecutionResult(details={"planned": True}, error="Dry-run: remediation not executed")
        return await self.commands.run(remediation.command, remediation.timeout)
