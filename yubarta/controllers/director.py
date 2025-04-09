import asyncio
from typing import Any

from aiokafka import AIOKafkaConsumer
from contextlib import asynccontextmanager


class Director:
    def __init__(self, kafka_broker: str, topic: str):
        self.kafka_broker = kafka_broker
        self.topic = topic

    async def run(self):
        consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=self.kafka_broker,
            group_id="director-group"
        )
        await consumer.start()
        try:
            async for message in consumer:
                print(message, "message")
                alarm_data = self.process_message(message.value)
                if self.should_execute_remediation(alarm_data):
                    await self.execute_remediation(alarm_data)
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


# Example usage
if __name__ == "__main__":
    director = Director(kafka_broker="kafka:9092", topic="alerts")
    asyncio.run(director.run())
