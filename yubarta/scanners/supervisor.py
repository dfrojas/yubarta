"""Scanner supervisor: owns scanner tasks, exposes status, handles shutdown."""

from __future__ import annotations

import asyncio

from yubarta.config import AppConfig
from yubarta.scanners.base import EventHandler, ScannerStatus
from yubarta.scanners.remote_command import RemoteCommandScanner
from yubarta.scanners.remote_file import RemoteFileScanner


class ScannerSupervisor:
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._scanners: list[RemoteFileScanner | RemoteCommandScanner] = []
        for index, watch in enumerate(config.watch):
            if getattr(watch, "kind", "log") == "log":
                self._scanners.append(
                    RemoteFileScanner(
                        name=f"log-{index}:{watch.file}",  # type: ignore[attr-defined]
                        target=config.target,
                        watch=watch,  # type: ignore[arg-type]
                    )
                )
            else:
                self._scanners.append(
                    RemoteCommandScanner(
                        name=f"command-{index}:{watch.run}",  # type: ignore[attr-defined]
                        target=config.target,
                        watch=watch,  # type: ignore[arg-type]
                    )
                )

    @property
    def scanners(self) -> list:
        return list(self._scanners)

    def statuses(self) -> list[ScannerStatus]:
        return [scanner.status for scanner in self._scanners]

    async def start(self, handler: EventHandler) -> None:
        await asyncio.gather(*(scanner.start(handler) for scanner in self._scanners))

    async def stop(self) -> None:
        await asyncio.gather(*(scanner.stop() for scanner in self._scanners))
