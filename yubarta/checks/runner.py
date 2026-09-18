"""Health checks: remote command + HTTP via httpx."""

from __future__ import annotations

import asyncio
import os

import httpx

from yubarta.config import CommandCheck, HttpCheck
from yubarta.execution.ssh import SSHConnectionFactory


class CheckOutcome:
    def __init__(self, name: str, passed: bool, detail: str, exit_code: int | None = None, status: int | None = None) -> None:
        self.name = name
        self.passed = passed
        self.detail = detail
        self.exit_code = exit_code
        self.status = status


def _resolve_http_headers(check: HttpCheck) -> dict[str, str]:
    headers: dict[str, str] = {}
    if check.auth is None:
        return headers
    if check.auth.bearer_from_env:
        token = os.environ.get(check.auth.bearer_from_env, "")
        if token:
            headers["Authorization"] = f"Bearer {token}"
    if check.auth.header_from_env:
        value = os.environ.get(check.auth.header_from_env, "")
        if value:
            headers[check.auth.header_name] = value
    return headers


async def run_check(
    check: CommandCheck | HttpCheck,
    executor: SSHConnectionFactory,
    http_client: httpx.AsyncClient | None = None,
) -> CheckOutcome:
    if isinstance(check, CommandCheck):
        try:
            result = await executor.run(check.run, timeout=30.0)
        except Exception as exc:
            return CheckOutcome(name=check.run, passed=False, detail=str(exc))
        passed = result.exit_code == check.expect_exit_code
        return CheckOutcome(
            name=check.run,
            passed=passed,
            detail=f"exit={result.exit_code} expected={check.expect_exit_code}",
            exit_code=result.exit_code,
        )
    headers = _resolve_http_headers(check)
    owns_client = http_client is None
    client = http_client or httpx.AsyncClient(timeout=check.timeout)
    try:
        response = await client.get(check.http, headers=headers)
        passed = response.status_code == check.expect_status
        return CheckOutcome(
            name=check.http,
            passed=passed,
            detail=f"status={response.status_code} expected={check.expect_status}",
            status=response.status_code,
        )
    except Exception as exc:
        return CheckOutcome(name=check.http, passed=False, detail=str(exc))
    finally:
        if owns_client:
            await client.aclose()


async def run_all_checks(
    checks: list[CommandCheck | HttpCheck],
    executor: SSHConnectionFactory,
    settle_delay: float = 0.0,
    interval: float = 5.0,
    timeout: float = 120.0,
) -> tuple[bool, list[CheckOutcome]]:
    """Poll until all checks pass or timeout. Returns (healthy, last_outcomes)."""
    if settle_delay > 0:
        await asyncio.sleep(settle_delay)
    deadline = asyncio.get_event_loop().time() + timeout
    last: list[CheckOutcome] = []
    async with httpx.AsyncClient() as client:
        while True:
            last = [await run_check(check, executor, client) for check in checks]
            if all(outcome.passed for outcome in last):
                return True, last
            if asyncio.get_event_loop().time() >= deadline:
                return False, last
            await asyncio.sleep(interval)


async def run_checks_once(
    checks: list[CommandCheck | HttpCheck],
    executor: SSHConnectionFactory,
) -> tuple[bool, list[CheckOutcome]]:
    async with httpx.AsyncClient() as client:
        outcomes = [await run_check(check, executor, client) for check in checks]
    return all(outcome.passed for outcome in outcomes), outcomes
