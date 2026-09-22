from yubarta.config.settings import LogWatch
from yubarta.controllers.scanners.base import BaseScanner, ReconnectPolicy
from yubarta.controllers.scanners.contracts import EventHandler, FileSource
from yubarta.controllers.scanners.parsing.multiline import MultilineAggregator
from yubarta.controllers.scanners.parsing.parsers import parse_line
from yubarta.core.models import NormalizedEvent
from yubarta.core.rules import matches_text


class RemoteFileScanner(BaseScanner):
    def __init__(
        self,
        name: str,
        target: str,
        watch: LogWatch,
        source: FileSource,
        reconnect: ReconnectPolicy | None = None,
    ) -> None:
        super().__init__(name, "log", target)
        self._watch = watch
        self._source = source
        self._reconnect = reconnect or ReconnectPolicy()
        self._seen_fingerprints: set[str] = set()

    async def _run(self, handler: EventHandler) -> None:
        attempt = 0
        aggregator = MultilineAggregator()
        while not self._stop.is_set():
            try:
                async with self._source.follow(self._watch.file, self._watch.backfill_lines) as lines:
                    self._note_connected()
                    attempt = 0
                    async for line in lines:
                        if not line.strip():
                            continue
                        logical = aggregator.feed(line)
                        if logical is not None:
                            await self._emit(logical, handler)
                    raise ConnectionError("remote tail stream ended unexpectedly")
            except (ConnectionError, TimeoutError, OSError) as exc:
                self._note_error(exc)
                attempt += 1
                await self._wait(self._reconnect.delay_for(attempt))

    async def _emit(self, logical_line: str, handler: EventHandler) -> None:
        parsed = parse_line(logical_line)
        event = NormalizedEvent(
            source=f"log:{self._watch.file}",
            target=self.status.target,
            message=parsed.message,
            raw=logical_line,
            level=parsed.level,
            fields={"file": self._watch.file, **parsed.fields},
        )
        fingerprint = event.fingerprint()
        if fingerprint in self._seen_fingerprints:
            return
        # Preserve source-specific filtering before the incident rule engine.
        if not matches_text(event.message, self._watch.match_any, self._watch.match_all):
            return
        await handler(event)
        self._seen_fingerprints.add(fingerprint)
        self._note_event()
