"""Yubarta runtime: one process owning scanners, rules, incidents, persistence."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from yubarta.config import AppConfig
from yubarta.diagnostics.runner import DiagnosticsRunner
from yubarta.events.models import NormalizedEvent
from yubarta.execution.ssh import AsyncSSHExecutor
from yubarta.incidents.service import IncidentService
from yubarta.persistence.session import create_engine, create_session_factory, init_db, resolve_database_url
from yubarta.rules.engine import RuleEngine
from yubarta.scanners.supervisor import ScannerSupervisor


@dataclass
class RuntimeServices:
    """Domain services owned by the runtime.

    Grouped so construction (and a future shutdown) stays in one place as the
    set grows. Add a field here, then wire it in YubartaRuntime._build_services.
    """

    incidents: IncidentService
    # diagnosis: DiagnosisService   # example: uncomment when the second service lands


class YubartaRuntime:
    def __init__(
        self,
        config: AppConfig,
        apply: bool = False,
        database_url: str = "",
        engine_options: dict | None = None,
    ) -> None:
        self._config = config
        self._apply = apply
        self._database_url = database_url or resolve_database_url(config.database_url)
        self._engine_options = engine_options or {}
        self._engine: AsyncEngine | None = None
        self._sessions: async_sessionmaker[AsyncSession] | None = None
        self._supervisor = ScannerSupervisor(config)
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
        self._engine = create_engine(self._database_url, **self._engine_options)
        await init_db(self._engine)
        self._db_healthy = True
        self._sessions = create_session_factory(self._engine)
        self._services = self._build_services()

    def _build_services(self) -> RuntimeServices:
        if self._sessions is None:
            raise RuntimeError("Runtime not set up")
        executor = AsyncSSHExecutor(self._config.target)
        return RuntimeServices(
            incidents=IncidentService(
                self._config,
                self._sessions,
                RuleEngine.from_watches(self._config.watch),
                executor,
                DiagnosticsRunner(executor, self._config.diagnostics),
                self._apply,
            ),
        )

    async def start_scanners(self) -> None:
        services = self.services

        async def _handler(event: NormalizedEvent) -> None:
            await services.incidents.handle_event(event)

        await self._supervisor.start(_handler)

    async def shutdown(self) -> None:
        await self._supervisor.stop()
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
        self._db_healthy = False

    @asynccontextmanager
    async def lifespan(self):  # type: ignore[no-untyped-def]
        await self.setup()
        await self.start_scanners()
        try:
            yield self
        finally:
            await self.shutdown()
