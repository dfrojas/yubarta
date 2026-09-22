import os
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import asyncssh
import pytest

from tests.support import Sandbox, free_port


@pytest.fixture(scope="session")
def sandbox(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Sandbox]:
    directory = tmp_path_factory.mktemp("sandbox")
    key = asyncssh.generate_private_key("ssh-ed25519")
    private = directory / "identity"
    public = directory / "identity.pub"
    private.write_bytes(key.export_private_key())
    private.chmod(0o600)
    public.write_bytes(key.export_public_key())
    environment = {**os.environ, "YUBARTA_TEST_PUBLIC_KEY": str(public),
                   "YUBARTA_TEST_DB_PORT": str(free_port()), "YUBARTA_TEST_SSH_PORT": str(free_port()),
                   "YUBARTA_TEST_HTTP_PORT": str(free_port())}
    known_hosts = directory / "known_hosts"
    sandbox = Sandbox(environment, f"yubarta-test-{uuid4().hex[:8]}", private, known_hosts)
    try:
        sandbox.compose("up", "--build", "--wait", "--wait-timeout", "90")
        host_key = sandbox.command("ssh-keygen", "-y", "-f", "/etc/ssh/ssh_host_ed25519_key").strip()
        known_hosts.write_text(f"[127.0.0.1]:{sandbox.ssh_port} {host_key}\n")
        yield sandbox
    finally:
        sandbox.compose("down", "--volumes", "--remove-orphans")
