#!/usr/bin/env python3
"""Simulate kernel swap activation without changing the Docker host's swap."""
from pathlib import Path
import sys

state = Path("/run/sandbox-swap")
if "--show" in sys.argv:
    if state.exists():
        swap = Path(state.read_text())
        print(f"{swap} {swap.stat().st_size}")
else:
    swap = Path(sys.argv[1])
    if not swap.is_file():
        raise SystemExit("Missing swap file")
    state.write_text(str(swap))
