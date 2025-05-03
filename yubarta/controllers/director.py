import asyncio
import json
from datetime import datetime
from typing import Any

from aiokafka import AIOKafkaConsumer

from yubarta.controllers.alarms import AlertController
from yubarta.drivers.db.orm import start_mappers
from yubarta.drivers.db.repository import SqlAlchemyAlarmRepository
from yubarta.drivers.db.sessions import get_raw_session
from yubarta.entrypoints.api_server.schemas import AlertRequest


class Director:
    def __init__(self, kafka_broker: str, topic: str):
        self.kafka_broker = kafka_broker
        self.topic = topic

    async def run(self) -> None:
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
                    # Parse the incoming JSON message into a pydantic request model.
                    alert_req = AlertRequest.model_validate(message.value)

                    received_at = datetime.utcnow()

                    alert_repository = SqlAlchemyAlarmRepository(session)

                    await AlertController(storage=alert_repository).process_alert(alert_req, received_at=received_at)
        finally:
            await consumer.stop()

    def process_message(self, message: Any) -> dict[str, Any]:
        # Process the incoming message and return structured alarm data
        return {}

    def should_execute_remediation(self, alarm_data: dict[str, Any]) -> bool:
        # Decision logic to determine if remediation should be executed
        return True

    async def execute_remediation(self, alarm_data: dict[str, Any]) -> None:
        # Logic to execute remediation
        pass


if __name__ == "__main__":
    start_mappers()
    director = Director(kafka_broker="kafka:9092", topic="alerts")
    asyncio.run(director.run())
