import asyncio
import logging

from yubarta.config.settings import Watch
from yubarta.controllers.scanners.contracts import EventCallback, StreamProcess
from yubarta.controllers.scanners.parsing.multiline import Multiline
from yubarta.controllers.scanners.parsing.parsers import parse
from yubarta.core.models import ScannerStatus, utcnow


class BaseScanner:
    def __init__(self, watch: Watch, target: str, callback: EventCallback):
        self.watch = watch
        self.target = target
        self.callback = callback
        self.status = ScannerStatus(name=watch.name, type=watch.kind, target=target)
        self.task: asyncio.Task[None] | None = None
        self.logger = logging.getLogger(__name__)

    def set_status(self, **values: object) -> None:
        self.status = self.status.model_copy(update=values)

    def start(self) -> None:
        self.task = asyncio.create_task(self.run(), name=f"scanner:{self.watch.name}")

    async def stop(self) -> None:
        if self.task:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
        self.set_status(state="stopped")

    async def run(self) -> None:
        delay = self.watch.reconnect_initial
        while True:
            session_started = asyncio.get_running_loop().time()
            self.set_status(state="connecting")
            try:
                await self.run_session()
                raise ConnectionError("Scanner stream ended")
            except asyncio.CancelledError:
                raise
            except Exception as error:
                # Boundary: a source or persistence failure must not silently kill scanning.
                self.logger.warning("Scanner %s disconnected: %s", self.watch.name, error)
                if asyncio.get_running_loop().time() - session_started >= self.watch.reconnect_max:
                    delay = self.watch.reconnect_initial
                self.set_status(state="reconnecting", reconnect_count=self.status.reconnect_count + 1,
                                last_error=str(error))
                await asyncio.sleep(delay)
                delay = min(delay * 2, self.watch.reconnect_max)

    def connected(self) -> None:
        self.set_status(state="connected", last_error=None)
        self.logger.info("Scanner %s connected", self.watch.name)

    async def emit(self, raw: str) -> None:
        event = parse(raw, self.watch.name, self.target, self.watch.parser)
        await self.callback(event, self.watch)
        self.set_status(last_event=utcnow())

    async def read_stream(self, process: StreamProcess) -> None:
        parser = Multiline(self.watch.parser.multiline)
        pending = asyncio.create_task(process.stdout.readline())
        try:
            while True:
                done, _ = await asyncio.wait({pending}, timeout=self.watch.parser.flush_after)
                if not done:
                    for raw in parser.flush():
                        await self.emit(raw)
                    continue
                line = pending.result()
                if not line:
                    for raw in parser.flush():
                        await self.emit(raw)
                    return
                for raw in parser.push(line):
                    await self.emit(raw)
                pending = asyncio.create_task(process.stdout.readline())
        finally:
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)

    async def run_session(self) -> None:
        raise NotImplementedError
