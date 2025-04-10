import asyncio
import json
from datetime import datetime
from typing import Any

from aiokafka import AIOKafkaConsumer

from yubarta.controllers.alarms import AlertController
from yubarta.core.models import Alert
from yubarta.drivers.db.orm import start_mappers
from yubarta.drivers.db.repository import SqlAlchemyAlarmRepository
from yubarta.drivers.db.sessions import get_raw_session


class Director:
    def __init__(self, kafka_broker: str, topic: str):
        self.kafka_broker = kafka_broker
        self.topic = topic

    async def run(self):
        consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=self.kafka_broker,
            group_id="director-group",
            value_deserializer=lambda v: json.loads(v),
        )
        await consumer.start()
        try:
            async for message in consumer:
                # TODO: Test performance with batches with a single session.
                async with get_raw_session() as session:
                    alert = Alert(**message.value)
                    alert.received_at = datetime.fromisoformat(alert.received_at)
                    alert.status_updated_at = datetime.fromisoformat(alert.status_updated_at)

                    alert_repository = SqlAlchemyAlarmRepository(session)

                    await AlertController(storage=alert_repository).process_alert(alert)
        finally:
            await consumer.stop()

    def process_message(self, message: Any) -> dict:
        # Process the incoming message and return structured alarm data
        return {}

    def should_execute_remediation(self, alarm_data: dict) -> bool:
        # Decision logic to determine if remediation should be executed
        return True

    async def execute_remediation(self, alarm_data: dict):
        # Logic to execute remediation
        pass


if __name__ == "__main__":
    start_mappers()
    director = Director(kafka_broker="kafka:9092", topic="alerts")
    asyncio.run(director.run())
