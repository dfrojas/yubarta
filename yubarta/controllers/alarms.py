from typing import Optional

from yubarta.config import settings
from yubarta.core.interfaces import AlarmMessagingInterface, AlarmStorageInterface
from yubarta.core.models import Alert
from yubarta.entrypoints.api_server.schemas import AlertKafkaMessage


class AlertController:
    def __init__(
        self, storage: Optional[AlarmStorageInterface] = None, messaging: Optional[AlarmMessagingInterface] = None
    ):
        self.storage = storage
        self.messaging = messaging

    async def process_alert(self, alert: Alert) -> Alert:
        if self.storage:
            await self.storage.add(alert)
            return alert
        elif self.messaging:
            kafka_msg = AlertKafkaMessage.from_domain(alert)
            await self.messaging.publish(
                topic=settings.KAFKA_ALERT_TOPIC, value=kafka_msg.model_dump_json(), key=kafka_msg.fingerprint
            )
            return alert
        else:
            raise ValueError("No storage or messaging provider configured")
