from yubarta.config.settings import CommandWatch
from yubarta.controllers.scanners.base import BaseScanner, ReconnectPolicy
from yubarta.controllers.scanners.contracts import CommandSource, EventHandler
from yubarta.core.models import NormalizedEvent


class RemoteCommandScanner(BaseScanner):
    def __init__(
        self,
        name: str,
        target: str,
        watch: CommandWatch,
        source: CommandSource,
        reconnect: ReconnectPolicy | None = None,
    ) -> None:
        super().__init__(name, "command", target)
        self._watch = watch
        self._source = source
        self._reconnect = reconnect or ReconnectPolicy()

    async def _run(self, handler: EventHandler) -> None:
        attempt = 0
        while not self._stop.is_set():
            try:
                async with self._source.connect() as executor:
                    self._note_connected()
                    attempt = 0
                    while not self._stop.is_set():
                        result = await executor.run(self._watch.run)
                        if result.exit_code != self._watch.expect_exit_code:
                            event = NormalizedEvent(
                                source=f"command:{self._watch.run}",
                                target=self.status.target,
                                message=f"Command failed (exit={result.exit_code}): {self._watch.run}\n{result.stdout.strip()}",
                                raw=result.stdout.strip() or f"exit={result.exit_code}",
                                fields={
                                    "command": self._watch.run,
                                    "exit_code": result.exit_code,
                                    "check_failed": True,
                                },
                            )
                            self._note_event()
                            await handler(event)
                        await self._wait(self._watch.interval_seconds())
            except (ConnectionError, TimeoutError, OSError) as exc:
                self._note_error(exc)
                attempt += 1
                await self._wait(self._reconnect.delay_for(attempt))
