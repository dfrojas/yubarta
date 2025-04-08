import asyncio
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from yubarta.config import settings
import logging

logger = logging.getLogger(__name__)

async def create_topics():
    """Create required Kafka topics if they don't exist"""
    admin_client = AIOKafkaAdminClient(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS
    )
    
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
    finally:
        await admin_client.close()

if __name__ == "__main__":
    asyncio.run(create_topics()) 