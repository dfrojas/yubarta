"""
Configuration to spin up an in-memory database for __unit__ testing purposes.

This module is intended to test logic but not external dependencies.
"""

from mockafka.aiokafka import FakeAIOKafkaProducer


class FakeDbRepository:
    def __init__(self):
        self.alerts = {}

    async def add(self, alert):
        self.alerts[alert.fingerprint] = alert

    async def get_all(self):
        return list(self.alerts.values())


class FakeKafkaRepository:
    def __init__(self):
        self.producer = FakeAIOKafkaProducer()
        self.started = False

    async def start(self):
        if not self.started:
            await self.producer.start()
            self.started = True

    async def stop(self):
        if self.started:
            await self.producer.stop()
            self.started = False

    async def publish(self, topic, value, key):
        if not self.started:
            await self.start()

        await self.producer.send_and_wait(topic, value=value, key=key)
