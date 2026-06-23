from yubarta.ingestion.store import InMemorySignalStore

_store = InMemorySignalStore()


def get_signal_store() -> InMemorySignalStore:
    return _store
