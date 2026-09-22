import asyncio
from unittest.mock import AsyncMock

import httpx
import pytest

from yubarta.config.settings import AppConfig, CommandCheck
from yubarta.controllers.checks import Checks
from yubarta.controllers.diagnostics import Diagnostics
from yubarta.controllers.incidents import Incidents
from yubarta.controllers.remediations.runner import Remediations
from yubarta.core.enums import IncidentState, StepKind, StepState
from yubarta.core.models import ExecutionResult, NormalizedEvent
from yubarta.drivers.db.sessions import Database
from yubarta.entrypoints.api_server.app import create_app
from yubarta.runtime import YubartaRuntime

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("healthy_at,apply,expected_steps,state", [(1, True, 0, "RESOLVED"), (2, True, 1, "RESOLVED"), (999, True, 3, "FAILED"), (999, False, 3, "FAILED")])
async def test_health_drives_ordered_remediation(database: Database, product_config: AppConfig,
                                                healthy_at: int, apply: bool, expected_steps: int, state: str) -> None:
    config = product_config.model_copy(update={"checks": [CommandCheck(run="health")], "diagnostics": ["diagnose"],
                                               "verify": product_config.verify.model_copy(update={"settle_delay": 0, "timeout": 0.01, "interval": 0.01})})
    commands = AsyncMock()
    check_count = 0

    async def execute(command: str, timeout: float) -> ExecutionResult:
        nonlocal check_count
        if command == "health":
            check_count += 1
            return ExecutionResult(exit_code=0 if check_count >= healthy_at else 1)
        return ExecutionResult(exit_code=0, passed=True)

    commands.run.side_effect = execute
    service = Incidents(config, database.uow, Diagnostics(commands, 1), Checks(commands, AsyncMock()), Remediations(commands, apply))
    event = NormalizedEvent(source="file", target="host", message="AH00957", raw="failure")
    await asyncio.gather(*(service.ingest(event.model_copy(update={"raw": f"failure {index}"}), config.watch[0]) for index in range(5)))
    await asyncio.gather(*service.tasks)
    incidents = await service.list()
    assert len(incidents) == 1 and incidents[0].state == state
    detail = await service.detail(incidents[0].id)
    steps = [step for step in detail.steps if step.kind == StepKind.REMEDIATION]
    assert len(steps) == expected_steps
    assert len(detail.events) == 5
    if not apply:
        assert all(step.state == StepState.SKIPPED for step in steps)
        assert [call.args[0] for call in commands.run.await_args_list] == ["diagnose", "health"]
    if healthy_at == 2:
        assert detail.resolved_by_step_id == steps[0].id
    if healthy_at == 1:
        assert detail.resolved_by_step_id is None


async def test_runtime_shutdown_auth_and_startup_recovery(database: Database, product_config: AppConfig) -> None:
    async with database.uow() as work:
        incident, _ = await work.repository.record_event(NormalizedEvent(source="old", target="host", raw="old failure", message="failure"), "tomcat-unavailable")
        await work.repository.start_step(incident.id, StepKind.REMEDIATION, "interrupted")
    runtime = YubartaRuntime(product_config)
    async with runtime.lifespan():
        recovered = await runtime.incidents.detail(incident.id)
        assert recovered.state == IncidentState.FAILED
        assert recovered.steps[0].state == StepState.FAILED
        app = create_app(runtime, manage_runtime=False)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            assert (await client.get("/health")).status_code == 200
            assert (await client.get("/status")).status_code == 401
            assert (await client.get("/api/v1/status", headers={"Authorization": "Bearer wrong"})).status_code == 401
            client.headers["Authorization"] = f"Bearer {product_config.api.token.get_secret_value()}"
            assert (await client.get("/api/v1/status")).json()["mode"] == "dry-run"
            assert (await client.get("/incidents/not-a-uuid")).status_code == 422
            assert (await client.get("/incidents/00000000-0000-0000-0000-000000000000")).status_code == 404
            assert "token" not in (await client.get("/status")).text
        for _ in range(100):
            if runtime.scanner_ssh.connections:
                break
            await asyncio.sleep(0.02)
        assert runtime.scanner_ssh.connections
    assert not runtime.running
    assert not runtime.scanner_ssh.connections and not runtime.execution_ssh.connections
    assert runtime.database.engine.pool.checkedout() == 0
    assert runtime.http.client.is_closed
    assert all(scanner.task.done() for scanner in runtime.supervisor.scanners)
