import httpx
import pytest

from yubarta.config.settings import HttpAuth, HttpCheck
from yubarta.drivers.network.http import HttpChecks


async def test_http_check_applies_expectation_auth_and_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_HEALTH_TOKEN", "test-token")

    def response(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-token"
        assert request.extensions["timeout"]["read"] == 0.25
        return httpx.Response(204)

    async with httpx.AsyncClient(transport=httpx.MockTransport(response)) as client:
        result = await HttpChecks(client).check(
            HttpCheck(
                http="http://target/health",
                expect_status=204,
                timeout=0.25,
                auth=HttpAuth(bearer_from_env="TEST_HEALTH_TOKEN"),
            )
        )
    assert result.passed and result.status == 204


async def test_http_timeout_is_an_unsuccessful_check() -> None:
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("health timeout", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(timeout)) as client:
        result = await HttpChecks(client).check(HttpCheck(http="http://target/health"))
    assert not result.passed and result.detail == "health timeout"
