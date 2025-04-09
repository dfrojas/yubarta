from yubarta.core.interfaces import AlarmMessagingInterface
from yubarta.drivers.messaging.kafka import producer


async def get_messaging() -> AlarmMessagingInterface:
    """FastAPI dependency for messaging"""
    # The producer is initialized during application startup via init_kafka
    # No need to check or start it here again.
    try:
        yield producer
    finally:
        # No need to close/stop the producer after each request
        # It's a long-lived connection
        pass
