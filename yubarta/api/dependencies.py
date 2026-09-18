"""Shared FastAPI dependencies for the Control API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request

from yubarta.persistence.repository import IncidentRepository
from yubarta.runtime import YubartaRuntime


def get_runtime(request: Request) -> YubartaRuntime:
    runtime: YubartaRuntime = request.app.state.runtime
    return runtime


RuntimeDep = Annotated[YubartaRuntime, Depends(get_runtime)]


async def get_incident_repository(runtime: RuntimeDep) -> AsyncIterator[IncidentRepository | None]:
    """Yield a repository, or ``None`` while the database is not available."""
    if runtime.sessions is None:
        yield None
        return
    async with runtime.sessions() as session:
        yield IncidentRepository(session)


IncidentRepositoryDep = Annotated[IncidentRepository | None, Depends(get_incident_repository)]
