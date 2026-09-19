"""Remote file scanner: tail -F equivalent over a long-lived AsyncSSH connection."""

from __future__ import annotations

import asyncio
import shlex
from datetime import UTC, datetime

import asyncssh

from yubarta.config import LogWatch, TargetConfig
from yubarta.events.models import NormalizedEvent
from yubarta.parsing.multiline import MultilineAggregator
from yubarta.parsing.parsers import parse_line
from yubarta.scanners.base import BaseScanner, EventHandler, ReconnectPolicy


class RemoteFileScanner(BaseScanner):
    """Follow a remote file with backfill + streaming + reconnect + normalization."""

    def __init__(
        self,
        name: str,
        target: TargetConfig,
        watch: LogWatch,
        reconnect: ReconnectPolicy | None = None,
    ) -> None:
        super().__init__(name=name, kind="log", target=target.host)
        self._target = target
        self._watch = watch
        self._reconnect = reconnect or ReconnectPolicy()
        self._seen_fingerprints: set[str] = set()

    def _connect_kwargs(self) -> dict:
        return {
            "host": self._target.host,
            "port": self._target.port,
            "username": self._target.user,
            "client_keys": [self._target.key] if self._target.key else None,
            "known_hosts": None,
            "password": self._target.password(),
            "keepalive_interval": 15.0,
        }

    async def _run(self, handler: EventHandler) -> None:
        attempt = 0
        aggregator = MultilineAggregator()
        while not self._stop.is_set():
            try:
                attempt += 1
                async with asyncssh.connect(**self._connect_kwargs()) as conn:
                    self._note_connected()
                    attempt = 0
                    await self._stream(conn, handler, aggregator)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # reconnect boundary
                self._note_error(str(exc))
                self._status.reconnect_count += 1
                delay = self._reconnect.delay_for(max(1, attempt))
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=delay)
                    return
                except TimeoutError:
                    continue

    async def _stream(
        self, conn: asyncssh.SSHClientConnection, handler: EventHandler, aggregator: MultilineAggregator
    ) -> None:
        backfill = self._watch.backfill_lines
        filename = shlex.quote(self._watch.file)
        # Backfill first, then live stream. tail -F semantic.
        backfill_cmd = f"tail -n {backfill} {filename}"
        try:
            result = await conn.run(backfill_cmd)
            if result.stdout:
                text = result.stdout if isinstance(result.stdout, str) else ""
                for line in text.splitlines():
                    await self._handle_line(line, handler, aggregator)
        except asyncssh.Error as exc:
            raise ConnectionError(f"backfill failed: {exc}") from exc
        # Live stream
        process = await conn.create_process(f"tail -n 0 -F {filename}")
        assert process.stdout is not None
        try:
            async for line in process.stdout:
                if self._stop.is_set():
                    break
                await self._handle_line(line.rstrip("\n"), handler, aggregator)
            if not self._stop.is_set():
                # tail -F must never EOF on its own; treat as a broken session.
                raise ConnectionError("remote tail stream ended unexpectedly")
        finally:
            process.terminate()

    async def _handle_line(self, line: str, handler: EventHandler, aggregator: MultilineAggregator) -> None:
        if not line.strip():
            return
        logical = aggregator.feed(line)
        if logical is None:
            return
        await self._emit(logical, handler)
        # feed() buffers the next record start; flush style: emit buffered continuations on next call.
        # Our aggregator returns the previous complete record when a new one starts and buffers the new
        # line internally, so nothing more to do here.

    async def _emit(self, logical_line: str, handler: EventHandler) -> None:
        parsed = parse_line(logical_line)
        event = NormalizedEvent(
            source=f"log:{self._watch.file}",
            target=self._target.host,
            observed_at=datetime.now(UTC),
            message=parsed.message,
            raw=logical_line,
            level=parsed.level,
            fields={"file": self._watch.file, **parsed.fields},
        )
        fingerprint = event.fingerprint()
        if fingerprint in self._seen_fingerprints:
            return
        self._seen_fingerprints.add(fingerprint)
        # Scanner-level match_any/match_all prefilter; rule engine decides incident type.
        if self._watch.match_any and not any(token in event.message for token in self._watch.match_any):
            if not self._watch.match_all:
                return
        if self._watch.match_all and not all(token in event.message for token in self._watch.match_all):
            return
        self._note_event()
        await handler(event)
