"""Polling preserves the last observation and respects a total deadline."""

from __future__ import annotations

import asyncio
import re
import subprocess
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx


async def eventually[T](
    description: str,
    observe: Callable[[], Awaitable[T]],
    accept: Callable[[T], bool],
    *,
    timeout: float = 30.0,
    interval: float = 0.2,
) -> T:
    last_value: T | None = None
    last_error: str | None = None
    try:
        async with asyncio.timeout(timeout):
            while True:
                try:
                    last_value = await observe()
                    if accept(last_value):
                        return last_value
                except (httpx.TransportError, OSError) as exc:
                    last_error = repr(exc)
                await asyncio.sleep(interval)
    except TimeoutError as exc:
        raise AssertionError(
            f"After {timeout}s waiting for {description}; "
            f"last observation={last_value!r}; last transport error={last_error}"
        ) from exc


async def http_status(url: str) -> int:
    async with httpx.AsyncClient(timeout=2.0, trust_env=False) as client:
        return (await client.get(url)).status_code


@dataclass
class Product:
    process: subprocess.Popen[str]
    log_path: Path
    apply: bool
    url: str = ""
    observations: dict[str, Any] = field(default_factory=dict)

    def assert_running(self) -> None:
        code = self.process.poll()
        if code is not None:
            raise AssertionError(f"Yubarta exited with code {code}:\n{self.logs()}")

    def logs(self) -> str:
        with self.log_path.open() as stream:
            return stream.read()

    async def discover_url(self) -> str:
        # Port 0 lets Uvicorn reserve its own port without a free-port race.
        self.assert_running()
        match = re.search(r"Uvicorn running on (http://127\.0\.0\.1:\d+)", self.logs())
        return match.group(1) if match else ""

    async def get(self, path: str) -> Any:
        self.assert_running()
        async with httpx.AsyncClient(timeout=2.0, trust_env=False) as client:
            response = await client.get(self.url + path)
            response.raise_for_status()
            data = response.json()
            self.observations[path] = data
            return data

    async def terminal_incident(self) -> dict[str, Any] | None:
        incidents = await self.get("/api/v1/incidents")
        if not incidents:
            return None
        assert len(incidents) == 1, (
            f"Expected one incident in isolated test: {incidents}"
        )
        detail = await self.get(f"/api/v1/incidents/{incidents[0]['id']}")
        if self.apply and detail["state"] == "FAILED":
            raise AssertionError(f"Recovery failed: {detail}")
        return detail
