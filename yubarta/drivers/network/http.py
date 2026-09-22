import httpx

from yubarta.config.settings import HTTPCheck
from yubarta.core.models import ExecutionResult


class HTTP:
    def __init__(self):
        self.client = httpx.AsyncClient(follow_redirects=False)

    async def check(self, check: HTTPCheck) -> ExecutionResult:
        try:
            async with self.client.stream("GET", check.http, timeout=check.timeout,
                                          headers={name: value.get_secret_value() for name, value in check.headers.items()}) as response:
                return ExecutionResult(passed=response.status_code == check.expect.status,
                                       details={"status": response.status_code, "expected_status": check.expect.status})
        except httpx.TimeoutException:
            return ExecutionResult(timed_out=True, error="HTTP check timed out")
        except httpx.HTTPError as error:
            # Do not persist request headers, credentials, or response bodies.
            return ExecutionResult(error=f"HTTP check failed: {type(error).__name__}")

    async def close(self) -> None:
        await self.client.aclose()
