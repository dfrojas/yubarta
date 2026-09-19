import asyncio
from collections.abc import Sequence

from yubarta.controllers.scanners.contracts import EventHandler, Scanner, ScannerStatus


class ScannerSupervisor:
    def __init__(self, scanners: Sequence[Scanner]) -> None:
        self._scanners = tuple(scanners)

    @property
    def scanners(self) -> tuple[Scanner, ...]:
        return self._scanners

    def statuses(self) -> list[ScannerStatus]:
        return [scanner.status for scanner in self._scanners]

    async def start(self, handler: EventHandler) -> None:
        # Sequential startup permits complete cleanup if a later scanner fails.
        try:
            for scanner in self._scanners:
                await scanner.start(handler)
        except BaseException:
            await self.stop()
            raise

    async def stop(self) -> None:
        results = await asyncio.gather(*(scanner.stop() for scanner in self._scanners), return_exceptions=True)
        errors = [result for result in results if isinstance(result, BaseException)]
        if errors:
            raise BaseExceptionGroup("Scanner shutdown failed", errors)
