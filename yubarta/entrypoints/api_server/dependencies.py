from typing import Annotated

from fastapi import Depends, Request

from yubarta.controllers.incidents import IncidentService
from yubarta.runtime import YubartaRuntime


def get_runtime(request: Request) -> YubartaRuntime:
    return request.app.state.runtime


RuntimeDep = Annotated[YubartaRuntime, Depends(get_runtime)]


def get_incident_service(runtime: RuntimeDep) -> IncidentService:
    return runtime.services.incidents


IncidentServiceDep = Annotated[IncidentService, Depends(get_incident_service)]
