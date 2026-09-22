import re


class Multiline:
    def __init__(self, enabled: bool):
        self.enabled = enabled
        self.buffer = ""

    def push(self, line: str) -> list[str]:
        line = line.rstrip("\r\n")
        if not self.enabled:
            return [line]
        continuation = re.match(r"^(\s+|Caused by:|Suppressed:|\.\.\. \d+ more)", line)
        # ponytail: stack traces split at 64 KiB; add disk spooling for larger events.
        if continuation and self.buffer and len(self.buffer) + len(line) < 65536:
            self.buffer += "\n" + line
            return []
        previous = self.flush()
        self.buffer = line[:65536]
        return previous

    def flush(self) -> list[str]:
        previous = [self.buffer] if self.buffer else []
        self.buffer = ""
        return previous
