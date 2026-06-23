from yubarta.domain.signal import Signal


class InMemorySignalStore:
    def __init__(self) -> None:
        self._store: dict[str, Signal] = {}

    async def add(self, signal: Signal) -> Signal:
        self._store.setdefault(signal.id, signal)
        return self._store[signal.id]

    async def get(self, signal_id: str) -> Signal | None:
        return self._store.get(signal_id)
