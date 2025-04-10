from dataclasses import asdict
from typing import Optional

from yubarta.config import settings
from yubarta.core.interfaces import AlarmMessagingInterface, AlarmStorageInterface
from yubarta.core.models import Alert


class AlertController:
    def __init__(
        self, storage: Optional[AlarmStorageInterface] = None, messaging: Optional[AlarmMessagingInterface] = None
    ):
        self.storage = storage
        self.messaging = messaging

    async def process_alert(self, alert: Alert):
        if self.storage:
            await self.storage.add(alert)

        if self.messaging:
            await self.messaging.publish(topic=settings.KAFKA_ALERT_TOPIC, value=asdict(alert), key=alert.fingerprint)
