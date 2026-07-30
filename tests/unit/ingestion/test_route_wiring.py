"""The webhook route depends on the storage port, never on its implementation.

A static check rather than a behavioural one, because the thing being protected is an
import: injecting the store correctly at runtime does not stop someone from reaching
for `SqlAlchemyIncidentStore` directly in a later edit, and that import is what would
put SQLAlchemy back into the ingestion capability.
"""

import inspect

from yubarta.ingestion.routes import webhook


def test_route_module_does_not_reference_the_concrete_store():
    source = inspect.getsource(webhook)

    assert "SqlAlchemyIncidentStore" not in source
    assert "sqlalchemy" not in source.lower()


def test_route_module_imports_the_storage_protocol():
    source = inspect.getsource(webhook)

    assert "from yubarta.domain.ports import IncidentStore" in source
