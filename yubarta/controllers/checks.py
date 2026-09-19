import asyncio
from typing import Protocol

from yubarta.config.settings import CommandCheck, HttpCheck, VerifyConfig
from yubarta.core.interfaces import CommandExecutor
from yubarta.core.models import CheckOutcome


class HttpChecker(Protocol):
    async def check(self, check: HttpCheck) -> CheckOutcome: ...


async def run_check(
    check: CommandCheck | HttpCheck,
    executor: CommandExecutor,
    http_checker: HttpChecker | None = None,
) -> CheckOutcome:
    if isinstance(check, HttpCheck):
        if http_checker is None:
            raise ValueError("HTTP checks require an HTTP checker")
        return await http_checker.check(check)
    try:
        result = await executor.run(check.run, timeout=30.0)
    except (ConnectionError, TimeoutError, OSError) as exc:
        return CheckOutcome(name=check.run, passed=False, detail=str(exc))
    return CheckOutcome(
        name=check.run,
        passed=result.exit_code == check.expect_exit_code,
        detail=f"exit={result.exit_code} expected={check.expect_exit_code}",
        exit_code=result.exit_code,
    )


class ChecksRunner:
    def __init__(
        self, checks: list[CommandCheck | HttpCheck], executor: CommandExecutor, http_checker: HttpChecker
    ) -> None:
        self._checks = checks
        self._executor = executor
        self._http_checker = http_checker

    async def run_once(self) -> tuple[bool, list[CheckOutcome]]:
        outcomes = [await run_check(check, self._executor, self._http_checker) for check in self._checks]
        return all(outcome.passed for outcome in outcomes), outcomes

    async def verify(self, config: VerifyConfig) -> tuple[bool, list[CheckOutcome]]:
        if config.settle_delay:
            await asyncio.sleep(config.settle_delay)
        loop = asyncio.get_running_loop()
        deadline = loop.time() + config.timeout
        while True:
            healthy, outcomes = await self.run_once()
            if healthy or loop.time() >= deadline:
                return healthy, outcomes
            await asyncio.sleep(min(config.interval, max(0.0, deadline - loop.time())))
