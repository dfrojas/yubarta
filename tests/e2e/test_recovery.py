import asyncio
import json
import os
import subprocess
import sys

import httpx
import pytest

from tests.support import Daemon, Sandbox
from yubarta.drivers.network.ssh import SSH

pytestmark = pytest.mark.e2e


async def test_real_ssh_recovery_and_cli_timeline(daemon: Daemon, ssh: SSH, sandbox: Sandbox) -> None:
    async with httpx.AsyncClient() as client:
        assert (await client.get(sandbox.http_url)).status_code == 200
    assert (await ssh.run("sudo -n sandbox-control fail", 5)).passed
    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.HTTPError):
            await client.get(sandbox.http_url)
    detail = await daemon.wait_incident("RESOLVED")
    assert detail["incident_type"] == "tomcat-unavailable"
    assert len(detail["events"]) == 1
    assert "AH00957" in detail["events"][0]["raw"]
    steps = detail["steps"]
    assert [step["sequence"] for step in steps] == list(range(1, len(steps) + 1))
    diagnostics = [step for step in steps if step["kind"] == "diagnostic"]
    assert len(diagnostics) == 4 and all(step["finished_at"] for step in diagnostics)
    assert diagnostics[0]["stdout"] and diagnostics[-1]["exit_code"] == 3
    prechecks = [step for step in steps if step["kind"] == "precheck"]
    assert len(prechecks) == 2 and all(step["state"] == "FAILED" for step in prechecks)
    remediations = [step for step in steps if step["kind"] == "remediation"]
    assert [step["name"] for step in remediations] == ["ensure-swap", "fix-restart-policy", "restart-tomcat"]
    assert all(step["state"] == "SUCCEEDED" and step["exit_code"] == 0 for step in remediations)
    assert detail["resolved_by_step_id"] == remediations[-1]["id"]
    for previous, following in zip(remediations, remediations[1:]):
        checks = [step for step in steps if previous["sequence"] < step["sequence"] < following["sequence"]]
        assert len(checks) >= 2 and all(step["kind"] == "verification" and not step["result"]["passed"] for step in checks)
    final_checks = steps[remediations[-1]["sequence"]:]
    assert len(final_checks) >= 2 and all(step["state"] == "SUCCEEDED" for step in final_checks[-2:])
    assert (await ssh.run("sudo -n systemctl is-active --quiet tomcat9", 5)).passed
    async with httpx.AsyncClient() as client:
        assert (await client.get(sandbox.http_url)).status_code == 200
    for command in ["health", "status", "scanners", "incidents", "incident"]:
        args = [sys.executable, "-m", "yubarta.main", "--server", daemon.url, command]
        if command == "incident":
            args.append(detail["id"])
        result = await asyncio.to_thread(subprocess.run, args, env={**os.environ, "YUBARTA_API_TOKEN": daemon.token}, capture_output=True, text=True, timeout=10)
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)
    # Repeat the real scripts: files and effective policy must remain stable.
    before = await asyncio.to_thread(sandbox.command, "stat", "-c", "%Y:%s", "/swapfile-yubarta", "/etc/systemd/system/tomcat9.service.d/zz-yubarta.conf")
    assert (await ssh.run("sudo -n /opt/yubarta/ensure-swap", 10)).passed
    assert (await ssh.run("sudo -n /opt/yubarta/fix-tomcat-restart-policy", 10)).passed
    after = await asyncio.to_thread(sandbox.command, "stat", "-c", "%Y:%s", "/swapfile-yubarta", "/etc/systemd/system/tomcat9.service.d/zz-yubarta.conf")
    assert before == after and "2147483648" in after
    persistent = await asyncio.to_thread(sandbox.command, "python3", "-c", "from pathlib import Path; print(Path('/etc/fstab').read_text().count('/swapfile-yubarta'))")
    assert persistent.strip() == "1"
    await daemon.stop()
    await daemon.start()
    assert (await daemon.get(f"/incidents/{detail['id']}"))["steps"] == detail["steps"]


@pytest.mark.parametrize("daemon", [False], indirect=True)
async def test_dryrun_records_plan_without_mutation(daemon: Daemon, ssh: SSH, sandbox: Sandbox) -> None:
    assert (await ssh.run("sudo -n sandbox-control fail", 5)).passed
    detail = await daemon.wait_incident("FAILED")
    planned = [step for step in detail["steps"] if step["kind"] == "remediation"]
    assert len(planned) == 3 and all(step["state"] == "SKIPPED" for step in planned)
    assert detail["resolved_by_step_id"] is None
    assert not (await ssh.run("sudo -n systemctl is-active --quiet tomcat9", 5)).passed
    assert (await ssh.run("test ! -e /swapfile-yubarta && test ! -e /etc/systemd/system/tomcat9.service.d/zz-yubarta.conf", 5)).passed
    assert (await daemon.get("/status"))["mode"] == "dry-run"
