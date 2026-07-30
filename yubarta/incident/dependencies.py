from fastapi import Request

from yubarta.infra.db.repository import SqlAlchemyIncidentStore


def get_incident_store(request: Request) -> SqlAlchemyIncidentStore:
    """Build the store over the unit of work the lifespan put on `app.state`.

    The engine and session factory belong to the application, the store does not
    own them, and routes never see either.
    """
    return SqlAlchemyIncidentStore(request.app.state.unit_of_work)
