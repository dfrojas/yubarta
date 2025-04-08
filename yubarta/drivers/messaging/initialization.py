from aiokafka.admin import AIOKafkaAdminClient, NewTopic
import logging
from contextlib import asynccontextmanager
from yubarta.config import settings
from yubarta.drivers.messaging.kafka import producer

logger = logging.getLogger(__name__)


class KafkaAdmin:
    def __init__(self, bootstrap_servers: str = settings.KAFKA_BOOTSTRAP_SERVERS):
        self.bootstrap_servers = bootstrap_servers
        self.admin_client = None

    @asynccontextmanager
    async def get_admin_client(self):
        """Get an admin client for Kafka operations"""
        admin_client = AIOKafkaAdminClient(
            bootstrap_servers=self.bootstrap_servers
        )
        try:
            await admin_client.start()
            yield admin_client
        finally:
            await admin_client.close()

    async def create_topics(self):
        """Create required Kafka topics if they don't exist"""
        async with self.get_admin_client() as admin_client:
            try:
                # Create topics with proper configuration
                topics = [
                    NewTopic(
                        name=settings.KAFKA_ALERT_TOPIC,
                        num_partitions=3,  # Start with 3 partitions for parallelism
                        replication_factor=1  # Single replica for dev, increase for prod
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


async def init_kafka(bootstrap_servers: str = settings.KAFKA_BOOTSTRAP_SERVERS):
    """Initialize Kafka setup and return a KafkaAdmin instance"""
    kafka_admin = KafkaAdmin(bootstrap_servers)
    await producer.start()
    await kafka_admin.create_topics()
    return kafka_admin
