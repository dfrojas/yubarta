import os

import httpx

from yubarta.config.settings import HttpCheck
from yubarta.core.models import CheckOutcome


class HttpChecks:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def check(self, check: HttpCheck) -> CheckOutcome:
        headers: dict[str, str] = {}
        if check.auth is not None:
            if check.auth.bearer_from_env:
                token = os.environ.get(check.auth.bearer_from_env, "")
                if token:
                    headers["Authorization"] = f"Bearer {token}"
            if check.auth.header_from_env:
                value = os.environ.get(check.auth.header_from_env, "")
                if value:
                    headers[check.auth.header_name] = value
        try:
            response = await self._client.get(check.http, headers=headers, timeout=check.timeout)
        except httpx.HTTPError as exc:
            return CheckOutcome(name=check.http, passed=False, detail=str(exc))
        return CheckOutcome(
            name=check.http,
            passed=response.status_code == check.expect_status,
            detail=f"status={response.status_code} expected={check.expect_status}",
            status=response.status_code,
        )
