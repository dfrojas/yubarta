import asyncio

from yubarta.controllers.scanners.contracts import Scanner
from yubarta.core.models import ScannerStatus


class ScannerSupervisor:
    def __init__(self, scanners: list[Scanner]):
        self.scanners = scanners

    def start(self) -> None:
        for scanner in self.scanners:
            scanner.start()

    async def stop(self) -> None:
        await asyncio.gather(*(scanner.stop() for scanner in self.scanners))

    def statuses(self) -> list[ScannerStatus]:
        return [scanner.status for scanner in self.scanners]
