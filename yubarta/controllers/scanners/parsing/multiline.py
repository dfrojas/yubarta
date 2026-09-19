"""Simple multiline aggregation for Java stack traces."""

from __future__ import annotations


class MultilineAggregator:
    """Aggregate Java stack trace continuation lines onto the parent line."""

    def __init__(self) -> None:
        self._buffer: str | None = None

    @staticmethod
    def _is_continuation(line: str) -> bool:
        if line.startswith((" ", "\t")):
            return True
        stripped = line.strip()
        return stripped.startswith(("at ", "Caused by:", "Suppressed:", "... "))

    def feed(self, line: str) -> str | None:
        """Feed one line. Returns a complete logical line or None when buffered."""
        if self._buffer is None:
            if self._is_continuation(line):
                self._buffer = line
                return None
            return line
        if self._is_continuation(line):
            self._buffer += "\n" + line
            return None
        complete = self._buffer
        self._buffer = None
        if self._is_continuation(line):
            self._buffer = line
            return complete
        # current line starts a new record; flush buffer and return it,
        # caller must feed the new line again — simplified: return buffer, buffer new
        self._buffer = line
        return complete

    def flush(self) -> str | None:
        buffered = self._buffer
        self._buffer = None
        return buffered
