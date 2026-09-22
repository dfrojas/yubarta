import shlex
from contextlib import AbstractAsyncContextManager

import asyncssh

from yubarta.config.settings import LogWatch
from yubarta.drivers.network.ssh import SSH


class RemoteFileSource:
    def __init__(self, ssh: SSH, watch: LogWatch):
        self.ssh = ssh
        self.watch = watch

    def open(self) -> AbstractAsyncContextManager[asyncssh.SSHClientProcess[str]]:
        # One tail avoids a gap between separate backfill and follow commands.
        return self.ssh.stream(f"tail -n {self.watch.backfill} -F -- {shlex.quote(self.watch.file)}")
