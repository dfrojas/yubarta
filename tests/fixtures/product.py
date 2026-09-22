import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4

import pytest
import yaml

from tests.support import Daemon, Sandbox, free_port
from yubarta.config.settings import AppConfig
from yubarta.drivers.config.loader import load_config
from yubarta.drivers.network.ssh import SSH


@pytest.fixture
def config_data() -> dict:
    return {
        "database_url": "postgresql+asyncpg://yubarta@localhost/yubarta",
        "target": {"host": "example.invalid", "user": "yubarta", "key": "/tmp/key"},
        "watch": [{"log": {"file": "/var/log/apache2/error.log", "match_any": ["AH00957", "AJP", "OutOfMemoryError"]}}],
        "diagnostics": ["uptime", "df -h /", "free -h", "sudo -n systemctl status tomcat9 --no-pager -l"],
        "checks": [{"run": "sudo -n systemctl is-active --quiet tomcat9", "expect": {"exit_code": 0}},
                   {"http": "http://example.invalid/health", "expect": {"status": 200}}],
        "remediations": [{"name": "ensure-swap", "command": "sudo -n /opt/yubarta/ensure-swap"},
                         {"name": "fix-restart-policy", "command": "sudo -n /opt/yubarta/fix-tomcat-restart-policy"},
                         {"name": "restart-tomcat", "command": "sudo -n systemctl restart tomcat9"}],
        "verify": {"settle_delay": "100ms", "interval": "100ms", "timeout": "400ms"},
        "shutdown_timeout": "1s",
    }


@pytest.fixture
def product_config(config_data: dict, database_url: str, sandbox: Sandbox, tmp_path: Path) -> AppConfig:
    config_data["database_url"] = database_url
    config_data["target"] = {"host": "127.0.0.1", "port": sandbox.ssh_port, "user": "yubarta",
                             "key": str(sandbox.key), "known_hosts": str(sandbox.known_hosts)}
    config_data["checks"][1]["http"] = sandbox.http_url
    config_data["watch"][0]["log"].update(reconnect_initial="1s", reconnect_max="2s")
    config_data["api"] = {"host": "127.0.0.1", "port": free_port(), "token": uuid4().hex}
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config_data))
    return load_config(path)


@pytest.fixture
async def ssh(product_config: AppConfig) -> AsyncIterator[SSH]:
    ssh = SSH(product_config.target)
    try:
        yield ssh
    finally:
        await ssh.close()


@pytest.fixture
async def daemon(product_config: AppConfig, sandbox: Sandbox, tmp_path: Path,
                 request: pytest.FixtureRequest) -> AsyncIterator[Daemon]:
    await asyncio.to_thread(sandbox.reset)
    daemon = Daemon(tmp_path / "config.yaml", f"http://127.0.0.1:{product_config.api.port}",
                    product_config.api.token.get_secret_value(), tmp_path / "daemon.log", getattr(request, "param", True))
    try:
        await daemon.start()
        await daemon.wait_scanner()
        yield daemon
    finally:
        await daemon.stop()
