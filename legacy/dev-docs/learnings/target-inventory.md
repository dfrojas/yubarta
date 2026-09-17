# Learning Note: target-inventory

## `lru_cache` over a module-level singleton for the inventory dependency

`ingestion/dependencies.py` builds its singleton eagerly at import time (`_store = InMemorySignalStore()`), which works because constructing an in-memory store can't fail. Loading the inventory can fail (missing file, bad YAML/schema), so `get_inventory()` uses `@lru_cache` instead — the file is only read on first call, not on import. This avoids failing every test that imports the module transitively, even ones that never touch the inventory.
