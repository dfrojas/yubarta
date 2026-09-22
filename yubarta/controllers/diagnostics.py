from yubarta.core.interfaces import CommandPort
from yubarta.core.models import ExecutionResult


class Diagnostics:
    def __init__(self, commands: CommandPort, timeout: float):
        self.commands = commands
        self.timeout = timeout

    async def run(self, command: str) -> ExecutionResult:
        return await self.commands.run(command, self.timeout)
