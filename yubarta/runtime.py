from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import monotonic

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from yubarta.config.settings import AppConfig, LogWatch
from yubarta.controllers.checks import Checks
from yubarta.controllers.diagnostics import Diagnostics
from yubarta.controllers.incidents import Incidents
from yubarta.controllers.remediations.runner import Remediations
from yubarta.controllers.scanners.remote_command import RemoteCommandScanner
from yubarta.controllers.scanners.remote_file import RemoteFileScanner
from yubarta.controllers.scanners.supervisor import ScannerSupervisor
from yubarta.drivers.db.initialization import migrate
from yubarta.drivers.db.sessions import Database
from yubarta.drivers.network.files import RemoteFileSource
from yubarta.drivers.network.http import HTTP
from yubarta.drivers.network.ssh import SSH


class YubartaRuntime:
    def __init__(self, config: AppConfig, apply: bool = False):
        self.config = config
        self.apply = apply
        self.started_at = monotonic()
        self.database = Database(config.database_url.get_secret_value())
        self.scanner_ssh = SSH(config.target)
        self.execution_ssh = SSH(config.target)
        self.http = HTTP()
        self.incidents = Incidents(config, self.database.uow,
            Diagnostics(self.execution_ssh, config.diagnostic_timeout),
            Checks(self.execution_ssh, self.http), Remediations(self.execution_ssh, apply))
        scanners = []
        for watch in config.watch:
            if isinstance(watch, LogWatch):
                scanners.append(RemoteFileScanner(watch, config.target.host, self.incidents.ingest,
                                                  RemoteFileSource(self.scanner_ssh, watch)))
            else:
                scanners.append(RemoteCommandScanner(watch, config.target.host, self.incidents.ingest, self.scanner_ssh))
        self.supervisor = ScannerSupervisor(scanners)
        self.running = False

    async def database_healthy(self) -> bool:
        try:
            async with self.database.engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            return True
        except (SQLAlchemyError, OSError):
            return False

    @asynccontextmanager
    async def lifespan(self) -> AsyncIterator[None]:
        try:
            await migrate(self.config.database_url.get_secret_value())
            await self.incidents.recover_interrupted()
            self.started_at = monotonic()
            self.supervisor.start()
            self.running = True
            yield
        finally:
            self.incidents.accepting = False
            await self.supervisor.stop()
            await self.scanner_ssh.close()
            await self.incidents.stop()
            await self.execution_ssh.close()
            await self.http.close()
            await self.database.close()
            self.running = False
