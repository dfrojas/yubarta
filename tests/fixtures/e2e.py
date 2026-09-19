"""E2E fixtures: Java sandbox and Yubarta process under test."""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import uuid
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest

from tests.e2e.docker_sandbox import Sandbox, build_image, docker, mapped_port
from tests.e2e.support import Product, eventually, http_status


@pytest.fixture(scope="session")
def java_image() -> Iterator[str]:
    if shutil.which("docker") is None:
        pytest.fail("Docker is required for E2E tests")
    docker("info", "--format", "{{.ServerVersion}}")
    image = f"yubarta-e2e-java:{uuid.uuid4().hex[:12]}"
    try:
        build_image(image)
        yield image
    finally:
        # Removing the session tag keeps cached build layers for the next run.
        subprocess.run(["docker", "image", "rm", image], capture_output=True, timeout=15)


@pytest.fixture
async def java_target(java_image: str, request: pytest.FixtureRequest) -> AsyncIterator[Sandbox]:
    name = f"yubarta-e2e-{uuid.uuid4().hex[:12]}"
    target: Sandbox | None = None
    try:
        docker(
            "run",
            "-d",
            "--name",
            name,
            "-p",
            "127.0.0.1::22",
            "-p",
            "127.0.0.1::8080",
            java_image,
        )
        target = Sandbox(name, mapped_port(name, 22), mapped_port(name, 8080))
        await eventually(
            "Java target HTTP 200",
            lambda: http_status(target.health_url),
            lambda status: status == 200,
        )
        yield target
    finally:
        if target is None:
            target = Sandbox(name, 0, 0)
        request.node.add_report_section("teardown", "Java target", target.diagnostics())
        docker("rm", "-f", name)


@pytest.fixture(params=[True, False], ids=["apply", "dry-run"])
async def product(
    java_target: Sandbox,
    test_db: str,
    tmp_path: Path,
    request: pytest.FixtureRequest,
) -> AsyncIterator[Product]:
    executable = shutil.which("yubarta")
    if executable is None:
        pytest.fail('Install the product first: python -m pip install -e ".[dev]"')
    config = Path(__file__).resolve().parents[1] / "e2e" / "scenarios" / "java" / "config.yaml"
    environment = {
        **os.environ,
        "YUBARTA_E2E_SSH_PORT": str(java_target.ssh_port),
        "YUBARTA_E2E_SSH_PASSWORD": "yubarta",
        "YUBARTA_E2E_HEALTH_URL": java_target.health_url,
        "YUBARTA_E2E_DATABASE_URL": test_db,
    }
    apply = bool(request.param)
    command = [executable, "serve", "--config", str(config)]
    if apply:
        command.append("--apply")
    log_path = tmp_path / "yubarta.log"
    with log_path.open("w") as output:
        process = subprocess.Popen(
            command,
            env=environment,
            cwd=tmp_path,
            stdout=output,
            stderr=subprocess.STDOUT,
            text=True,
        )
        instance = Product(process, log_path, apply)
        try:
            instance.url = await eventually("Yubarta listening", instance.discover_url, bool)
            await eventually(
                "SSH scanner connected",
                lambda: instance.get("/api/v1/scanners"),
                lambda scanners: len(scanners) == 1 and all(item["connected"] for item in scanners),
            )
            yield instance
        finally:
            forced = False
            if process.poll() is None:
                process.terminate()
                try:
                    await asyncio.to_thread(process.wait, timeout=10)
                except subprocess.TimeoutExpired:
                    forced = True
                    process.kill()
                    await asyncio.to_thread(process.wait, timeout=5)
            request.node.add_report_section("teardown", "Yubarta output", instance.logs())
            request.node.add_report_section("teardown", "Control API", repr(instance.observations))
            assert not forced, "Yubarta did not shut down within 10s; process was killed"
