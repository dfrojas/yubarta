from yubarta.core.interfaces import AlarmStorageInterface, AlarmMessagingInterface
from yubarta.core.models import Alert
from yubarta.drivers.messaging.kafka import producer
from yubarta.config import settings
from typing import Optional
from dataclasses import asdict
import json


class AlertController:
    def __init__(self,
        storage: Optional[AlarmStorageInterface] = None,
        messaging: Optional[AlarmMessagingInterface] = None):
        self.storage = storage
        self.messaging = messaging

    async def process_alert(self, alert: Alert):
        if self.storage:
            await self.storage.add(alert)

        if self.messaging:
            await self.messaging.publish(
                topic=settings.KAFKA_ALERT_TOPIC,
                value=json.dumps(asdict(alert)),
                key=alert.fingerprint
            )
