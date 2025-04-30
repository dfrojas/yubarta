from datetime import datetime
from typing import Optional

from yubarta.config import settings
from yubarta.core.interfaces import AlarmMessagingInterface, AlarmStorageInterface
from yubarta.core.models import Alert
from yubarta.entrypoints.api_server.schemas import AlertKafkaMessage, AlertRequest


class AlertController:
    def __init__(
        self, storage: Optional[AlarmStorageInterface] = None, messaging: Optional[AlarmMessagingInterface] = None
    ):
        self.storage = storage
        self.messaging = messaging

    async def process_alert(self, alert: AlertRequest, received_at: datetime) -> Alert:
        alert_domain = alert.to_domain(received_at)
        if self.storage:
            await self.storage.add(alert_domain)
            return alert_domain
        elif self.messaging:
            kafka_msg = AlertKafkaMessage.from_domain(alert_domain)
            await self.messaging.publish(
                topic=settings.KAFKA_ALERT_TOPIC, value=kafka_msg.model_dump_json(), key=kafka_msg.fingerprint
            )
            return alert_domain
        else:
            raise ValueError("No storage or messaging provider configured")
