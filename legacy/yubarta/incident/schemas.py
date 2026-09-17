from pydantic import BaseModel

from yubarta.incident.models import Incident, IncidentTransition


class IncidentDetail(BaseModel):
    """An incident plus its lifecycle log.

    The two are returned together because the denormalized current state answers
    "where is it now" and the log answers "how did it get here", and reading one
    without the other is what makes a stuck incident hard to explain.
    """

    incident: Incident
    transitions: list[IncidentTransition]
