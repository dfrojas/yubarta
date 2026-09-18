"""Product E2E: a killed JVM is recovered in apply mode and left down in dry-run.

Real product process, YAML, SSH, PostgreSQL, and Java. The AJP log line is
synthetic input; this scenario does not run Apache, Tomcat, or systemd.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import time

import httpx

from tests.e2e.docker_sandbox import Sandbox
from tests.e2e.support import Product, eventually, http_status


async def test_java_failure_is_audited_and_only_apply_recovers(
    java_target: Sandbox,
    product: Product,
) -> None:
    assert await http_status(java_target.health_url) == 200
    assert await product.get("/api/v1/incidents") == []
    pid_before = java_target.run("cat", "/run/yubarta-app/app.pid")
    assert pid_before.isdigit(), f"Invalid Java PID: {pid_before!r}"

    java_target.run("kill", "-9", pid_before)

    async def application_down() -> str:
        try:
            return f"HTTP {await http_status(java_target.health_url)}"
        except httpx.TransportError:
            return "unreachable"

    await eventually(
        "killed JVM to stop serving HTTP",
        application_down,
        lambda state: state != "HTTP 200",
    )
    # The test writes this input; no Apache process exists in the fast scenario.
    java_target.run(
        "sh",
        "-c",
        "echo '[proxy_ajp:error] AH00957: AJP: Connection refused' >> /var/log/apache2/error.log",
    )
    incident = await eventually(
        "incident terminal state",
        product.terminal_incident,
        lambda detail: detail is not None and detail["state"] in ("RESOLVED", "FAILED"),
        timeout=45.0,
    )
    assert incident is not None
    remediations = [step for step in incident["steps"] if step["kind"] == "remediation"]
    assert [step["name"] for step in remediations] == [
        "ensure-swap",
        "fix-restart-policy",
        "restart-app",
    ], incident

    if product.apply:
        assert incident["state"] == "RESOLVED", incident
        assert incident["resolved_by_step_id"] == remediations[-1]["id"], incident
        assert all(step["state"] == "SUCCEEDED" for step in remediations), incident
        assert any(step["kind"] == "verification" for step in incident["steps"]), (
            incident
        )
        pid_after = java_target.run("cat", "/run/yubarta-app/app.pid")
        assert pid_after.isdigit() and pid_after != pid_before, (pid_before, pid_after)
        await eventually(
            "recovered Java HTTP 200",
            lambda: http_status(java_target.health_url),
            lambda status: status == 200,
        )
    else:
        assert incident["state"] == "FAILED", incident
        assert all(step["state"] == "SKIPPED" for step in remediations), incident
        assert incident["resolved_by_step_id"] is None, incident
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            product.assert_running()
            assert await application_down() != "HTTP 200", (
                "Dry-run restarted the application"
            )
            await asyncio.sleep(0.2)

    # Smoke-test the installed CLI against the same running Control API.
    environment = dict(os.environ)
    environment.pop("YUBARTA_API_TOKEN", None)
    result = subprocess.run(
        ["yubarta", "incident", incident["id"], "--server", product.url],
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["state"] == incident["state"]
