import json
import logging
from typing import Any, Optional

from aiokafka import AIOKafkaProducer

from yubarta.config import settings

logger = logging.getLogger(__name__)


class KafkaProducer:
    def __init__(self):
        self.producer: Optional[AIOKafkaProducer] = None
        self.bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS

    async def start(self):
        """Initialize and start the Kafka producer"""
        if self.producer is None:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                compression_type=settings.KAFKA_COMPRESSION_TYPE,
                acks=settings.KAFKA_ACKS,
                max_batch_size=settings.KAFKA_MAX_BATCH_SIZE,
                max_request_size=settings.KAFKA_MAX_BATCH_SIZE * 2,
                retry_backoff_ms=settings.KAFKA_RETRY_BACKOFF_MS,
                value_serializer=lambda v: json.dumps(v).encode(),
            )
            await self.producer.start()
            logger.info("Kafka producer started successfully")

    async def stop(self):
        """Stop the Kafka producer"""
        if self.producer is not None:
            await self.producer.stop()
            self.producer = None
            logger.info("Kafka producer stopped")

    async def publish(self, topic: str, value: Any, key: Optional[str] = None) -> None:
        """Send a message to a Kafka topic

        Args:
            topic: The topic to send the message to
            value: The message value to send
            key: Optional message key for partitioning
        """
        if self.producer is None:
            raise RuntimeError("Kafka producer not started")

        try:
            key_bytes = key.encode("utf-8") if key else None
            await self.producer.send_and_wait(topic, value, key=key_bytes)
            logger.debug(f"Message sent to topic {topic}")
            await self.producer.stop()
        except Exception as e:
            logger.error(f"Failed to send message to Kafka: {str(e)}")
            raise


producer = KafkaProducer()
