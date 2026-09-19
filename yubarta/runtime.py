"""Yubarta runtime: one process owning scanners, rules, incidents, persistence."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass
from functools import partial

import httpx
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from yubarta.config.settings import AppConfig, LogWatch
from yubarta.controllers.checks import ChecksRunner
from yubarta.controllers.diagnostics import DiagnosticsRunner
from yubarta.controllers.incidents import IncidentService
from yubarta.controllers.remediations.runner import RemediationRunner
from yubarta.controllers.scanners.contracts import Scanner
from yubarta.controllers.scanners.remote_command import RemoteCommandScanner
from yubarta.controllers.scanners.remote_file import RemoteFileScanner
from yubarta.controllers.scanners.supervisor import ScannerSupervisor
from yubarta.core.models import NormalizedEvent
from yubarta.core.rules import RuleEngine
from yubarta.drivers.db.initialization import init_db
from yubarta.drivers.db.sessions import create_engine, create_session_factory, resolve_database_url
from yubarta.drivers.db.sqlalchemy import SqlAlchemyUnitOfWork
from yubarta.drivers.network.files import SSHFileSource
from yubarta.drivers.network.http import HttpChecks
from yubarta.drivers.network.ssh import AsyncSSHExecutor, SSHCommandSource


@dataclass
class RuntimeServices:
    """Application services constructed together at the composition root."""

    incidents: IncidentService


class YubartaRuntime:
    def __init__(
        self,
        config: AppConfig,
        apply: bool = False,
        database_url: str = "",
        engine_options: dict[str, object] | None = None,
    ) -> None:
        self._config = config
        self._apply = apply
        self._database_url = database_url or resolve_database_url(config.database_url)
        self._engine_options = engine_options or {}
        self._engine: AsyncEngine | None = None
        self._sessions: async_sessionmaker[AsyncSession] | None = None
        self._supervisor = ScannerSupervisor([])
        self._resources = AsyncExitStack()
        self._http_client: httpx.AsyncClient | None = None
        self._services: RuntimeServices | None = None
        self._started_at = time.monotonic()
        self._db_healthy = False

    @property
    def config(self) -> AppConfig:
        return self._config

    @property
    def apply(self) -> bool:
        return self._apply

    @property
    def supervisor(self) -> ScannerSupervisor:
        return self._supervisor

    @property
    def services(self) -> RuntimeServices:
        if self._services is None:
            raise RuntimeError("Runtime not set up")
        return self._services

    @property
    def uptime_seconds(self) -> float:
        return time.monotonic() - self._started_at

    @property
    def db_healthy(self) -> bool:
        return self._db_healthy

    @property
    def sessions(self) -> async_sessionmaker[AsyncSession]:
        if self._sessions is None:
            raise RuntimeError("Runtime not set up")
        return self._sessions

    async def setup(self) -> None:
        if self._engine is not None:
            raise RuntimeError("Runtime is already set up")
        try:
            self._engine = create_engine(self._database_url, **self._engine_options)
            self._resources.push_async_callback(self._engine.dispose)
            await init_db(self._engine)
            self._sessions = create_session_factory(self._engine)
            self._http_client = await self._resources.enter_async_context(httpx.AsyncClient())
            self._services = self._build_services()
            scanners: list[Scanner] = []
            for index, watch in enumerate(self._config.watch):
                if isinstance(watch, LogWatch):
                    scanners.append(
                        RemoteFileScanner(
                            name=f"log-{index}:{watch.file}",
                            target=self._config.target.host,
                            watch=watch,
                            source=SSHFileSource(self._config.target),
                        )
                    )
                else:
                    scanners.append(
                        RemoteCommandScanner(
                            name=f"command-{index}:{watch.run}",
                            target=self._config.target.host,
                            watch=watch,
                            source=SSHCommandSource(self._config.target),
                        )
                    )
            self._supervisor = ScannerSupervisor(scanners)
            self._resources.push_async_callback(self._supervisor.stop)
            self._started_at = time.monotonic()
            self._db_healthy = True
        except BaseException:
            await self.shutdown()
            raise

    def _build_services(self) -> RuntimeServices:
        if self._sessions is None or self._http_client is None:
            raise RuntimeError("Runtime not set up")
        executor = AsyncSSHExecutor(self._config.target)
        return RuntimeServices(
            incidents=IncidentService(
                self._config,
                partial(SqlAlchemyUnitOfWork, self._sessions),
                RuleEngine.from_watches(self._config.watch),
                DiagnosticsRunner(executor, self._config.diagnostics),
                ChecksRunner(self._config.checks, executor, HttpChecks(self._http_client)),
                RemediationRunner(executor, self._apply),
            ),
        )

    async def start_scanners(self) -> None:
        services = self.services

        async def _handler(event: NormalizedEvent) -> None:
            await services.incidents.handle_event(event)

        await self._supervisor.start(_handler)

    async def shutdown(self) -> None:
        try:
            await self._resources.aclose()
        finally:
            self._engine = None
            self._sessions = None
            self._http_client = None
            self._services = None
            self._db_healthy = False

    @asynccontextmanager
    async def lifespan(self) -> AsyncIterator[YubartaRuntime]:
        try:
            await self.setup()
            await self.start_scanners()
            yield self
        finally:
            await self.shutdown()
