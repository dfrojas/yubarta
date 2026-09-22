import asyncio
import os
from pathlib import Path
import socket
import subprocess
import sys
from typing import Any

import httpx


def free_port() -> int:
    with socket.socket() as connection:
        connection.bind(("127.0.0.1", 0))
        return connection.getsockname()[1]


class Sandbox:
    def __init__(self, environment: dict[str, str], project: str, key: Path, known_hosts: Path):
        self.environment = environment
        self.project = project
        self.key = key
        self.known_hosts = known_hosts
        self.ssh_port = int(environment["YUBARTA_TEST_SSH_PORT"])
        self.http_url = f"http://127.0.0.1:{environment['YUBARTA_TEST_HTTP_PORT']}"
        self.database_url = f"postgresql+asyncpg://yubarta@127.0.0.1:{environment['YUBARTA_TEST_DB_PORT']}/yubarta"

    def compose(self, *args: str) -> str:
        result = subprocess.run(["docker", "compose", "-p", self.project, *args], env=self.environment,
                                capture_output=True, text=True, timeout=240)
        if result.returncode:
            raise RuntimeError(f"Compose failed: {result.stdout}\n{result.stderr}")
        return result.stdout

    def command(self, *args: str) -> str:
        return self.compose("exec", "-T", "sandbox", *args)

    def reset(self) -> None:
        self.command("python3", "-c", "from pathlib import Path; Path('/var/log/apache2/error.log').write_text(''); "
                     "[Path(p).unlink(missing_ok=True) for p in ['/run/sandbox-swap', '/swapfile-yubarta', "
                     "'/run/effective-policy', '/etc/systemd/system/tomcat9.service.d/zz-yubarta.conf']]; "
                     "Path('/etc/fstab').write_text('')")
        self.command("systemctl", "restart", "tomcat9")


class Daemon:
    def __init__(self, config: Path, url: str, token: str, log: Path, apply: bool):
        self.url = url
        self.token = token
        self.log = log
        self.config = config
        self.apply = apply
        self.process: subprocess.Popen | None = None

    async def start(self) -> None:
        command = [sys.executable, "-m", "yubarta.main", "serve", "--config", str(self.config)]
        if self.apply:
            command.append("--apply")
        environment = {**os.environ, "YUBARTA_API_TOKEN": self.token}
        with self.log.open("ab") as output:
            self.process = subprocess.Popen(command, stdout=output, stderr=output, env=environment)
        async with httpx.AsyncClient() as client:
            for _ in range(200):
                if self.process.poll() is not None:
                    raise AssertionError(self.log.read_text())
                try:
                    if (await client.get(f"{self.url}/health")).status_code == 200:
                        return
                except httpx.HTTPError:
                    pass
                await asyncio.sleep(0.05)
        raise AssertionError(f"Daemon failed to start: {self.log.read_text()}")

    async def stop(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                await asyncio.wait_for(asyncio.to_thread(self.process.wait), 15)
            except TimeoutError:
                self.process.kill()
                await asyncio.to_thread(self.process.wait)
                raise AssertionError(f"Daemon shutdown hung: {self.log.read_text()}") from None

    async def get(self, path: str) -> Any:
        async with httpx.AsyncClient(base_url=self.url, headers={"Authorization": f"Bearer {self.token}"}) as client:
            response = await client.get(path)
            response.raise_for_status()
            return response.json()

    async def wait_scanner(self, state: str = "connected", reconnects: int = 0) -> dict:
        for _ in range(200):
            scanners = await self.get("/scanners")
            if scanners[0]["state"] == state and scanners[0]["reconnect_count"] >= reconnects:
                return scanners[0]
            await asyncio.sleep(0.05)
        raise AssertionError(f"Scanner did not reach {state}: {scanners}\n{self.log.read_text()}")

    async def wait_incident(self, state: str, count: int = 1) -> dict:
        for _ in range(300):
            incidents = await self.get("/incidents")
            if len(incidents) >= count and incidents[0]["state"] == state:
                return await self.get(f"/incidents/{incidents[0]['id']}")
            await asyncio.sleep(0.05)
        raise AssertionError(f"No {state} incident: {incidents}\n{self.log.read_text()}")
