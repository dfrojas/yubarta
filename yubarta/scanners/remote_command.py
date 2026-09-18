"""Remote command scanner: continuous or periodic remote commands over SSH."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import asyncssh

from yubarta.config import CommandWatch, TargetConfig
from yubarta.events.models import NormalizedEvent
from yubarta.scanners.base import BaseScanner, EventHandler, ReconnectPolicy


class RemoteCommandScanner(BaseScanner):
    def __init__(
        self,
        name: str,
        target: TargetConfig,
        watch: CommandWatch,
        reconnect: ReconnectPolicy | None = None,
    ) -> None:
        super().__init__(name=name, kind="command", target=target.host)
        self._target = target
        self._watch = watch
        self._reconnect = reconnect or ReconnectPolicy()

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
        interval = self._watch.interval_seconds()
        while not self._stop.is_set():
            try:
                async with asyncssh.connect(**self._connect_kwargs()) as conn:
                    self._note_connected()
                    attempt = 0
                    while not self._stop.is_set():
                        try:
                            result = await conn.run(self._watch.run)
                            exit_code = result.exit_status if result.exit_status is not None else 1
                            stdout = result.stdout if isinstance(result.stdout, str) else ""
                            if exit_code != self._watch.expect_exit_code:
                                event = NormalizedEvent(
                                    source=f"command:{self._watch.run}",
                                    target=self._target.host,
                                    observed_at=datetime.now(timezone.utc),
                                    message=f"Command failed (exit={exit_code}): {self._watch.run}\n{stdout.strip()}",
                                    raw=stdout.strip() or f"exit={exit_code}",
                                    fields={
                                        "command": self._watch.run,
                                        "exit_code": exit_code,
                                        "check_failed": True,
                                    },
                                )
                                self._note_event()
                                await handler(event)
                        except asyncssh.Error as exc:
                            raise ConnectionError(f"command scanner failed: {exc}") from exc
                        try:
                            await asyncio.wait_for(self._stop.wait(), timeout=interval)
                            return
                        except asyncio.TimeoutError:
                            continue
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._note_error(str(exc))
                self._status.reconnect_count += 1
                attempt += 1
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=self._reconnect.delay_for(attempt))
                    return
                except asyncio.TimeoutError:
                    continue
