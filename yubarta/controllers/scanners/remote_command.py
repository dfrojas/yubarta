import asyncio
from uuid import uuid4

from yubarta.config.settings import CommandWatch
from yubarta.controllers.scanners.base import BaseScanner
from yubarta.controllers.scanners.contracts import CommandSource, EventCallback
from yubarta.controllers.scanners.parsing.parsers import parse
from yubarta.core.models import utcnow


class RemoteCommandScanner(BaseScanner):
    def __init__(self, watch: CommandWatch, target: str, callback: EventCallback, source: CommandSource):
        super().__init__(watch, target, callback)
        self.watch = watch
        self.source = source

    async def run_session(self) -> None:
        if self.watch.interval is None:
            async with self.source.stream(self.watch.run) as process:
                self.connected()
                await self.read_stream(process)
            return
        while True:
            result = await self.source.run(self.watch.run, self.watch.timeout)
            if result.error:
                raise ConnectionError(result.error)
            self.connected()
            event = parse(result.stdout + result.stderr, self.watch.name, self.target, self.watch.parser)
            event = event.model_copy(update={"fields": {**event.fields, "exit_code": result.exit_code,
                                                         "sample_id": str(uuid4())}})
            await self.callback(event, self.watch)
            self.set_status(last_event=utcnow())
            await asyncio.sleep(self.watch.interval)
