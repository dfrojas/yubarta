import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, Optional

from aiokafka.admin import AIOKafkaAdminClient, NewTopic

from yubarta.config import settings
from yubarta.drivers.messaging.kafka import producer

logger = logging.getLogger(__name__)


class KafkaAdmin:
    """Utility class for Kafka administrative tasks (topic management, etc.)."""

    def __init__(self, bootstrap_servers: str = settings.KAFKA_BOOTSTRAP_SERVERS) -> None:
        self.bootstrap_servers = bootstrap_servers
        # The concrete type is ``AIOKafkaAdminClient`` but we mark it as ``Any``
        # because the library is untyped.
        self.admin_client: Optional[Any] = None

    @asynccontextmanager
    async def get_admin_client(self) -> AsyncGenerator[Any, None]:
        """Context-manager that yields an *aiokafka* admin client."""

        admin_client = AIOKafkaAdminClient(bootstrap_servers=self.bootstrap_servers)
        try:
            await admin_client.start()
            yield admin_client
        finally:
            await admin_client.close()

    async def create_topics(self) -> None:
        """Create required Kafka topics if they don't exist"""
        async with self.get_admin_client() as admin_client:
            try:
                # Create topics with proper configuration
                topics = [
                    NewTopic(
                        name=settings.KAFKA_ALERT_TOPIC,
                        num_partitions=3,  # Start with 3 partitions for parallelism
                        replication_factor=1,  # Single replica for dev, increase for prod
                    )
                ]

                await admin_client.create_topics(topics)
                logger.info(f"Successfully created topic: {settings.KAFKA_ALERT_TOPIC}")
            except Exception as e:
                if "already exists" in str(e):
                    logger.info(f"Topic {settings.KAFKA_ALERT_TOPIC} already exists")
                else:
                    logger.error(f"Failed to create Kafka topics: {str(e)}")
                    raise


async def init_kafka(bootstrap_servers: str = settings.KAFKA_BOOTSTRAP_SERVERS) -> KafkaAdmin:
    """Initialize Kafka infrastructure (producer + topics) and return an admin helper."""

    kafka_admin = KafkaAdmin(bootstrap_servers)
    await producer.start()
    await kafka_admin.create_topics()
    return kafka_admin
