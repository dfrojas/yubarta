from yubarta.config.settings import LogWatch
from yubarta.controllers.scanners.base import BaseScanner
from yubarta.controllers.scanners.contracts import EventCallback, FileSource


class RemoteFileScanner(BaseScanner):
    def __init__(self, watch: LogWatch, target: str, callback: EventCallback, source: FileSource):
        super().__init__(watch, target, callback)
        self.source = source

    async def run_session(self) -> None:
        async with self.source.open() as process:
            self.connected()
            await self.read_stream(process)
