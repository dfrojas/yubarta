from datetime import datetime

import pytest
from mockafka import asetup_kafka
from mockafka.aiokafka import FakeAIOKafkaConsumer

from tests.unit.fakes import FakeDbRepository, FakeKafkaRepository
from yubarta.config import settings
from yubarta.controllers.alarms import AlertController
from yubarta.entrypoints.api_server.schemas import AlertKafkaMessage

pytestmark = pytest.mark.unit


async def test_not_processed_alert_if_no_storage_or_messaging_provided(datadog_alert):
    with pytest.raises(ValueError) as e:
        fixed_time = datetime(2025, 4, 30, 12, 0, 0)
        controller = AlertController()
        await controller.process_alert(datadog_alert, received_at=fixed_time)
    assert str(e.value) == "No storage or messaging provider configured"


async def test_stores_alert_if_storage_provided(datadog_alert):
    storage = FakeDbRepository()
    controller = AlertController(storage=storage)

    fixed_time = datetime(2025, 4, 30, 12, 0, 0)
    alert_domain = await controller.process_alert(datadog_alert, received_at=fixed_time)
    assert storage.alerts[alert_domain.fingerprint] == alert_domain


@asetup_kafka(topics=[{"topic": settings.KAFKA_ALERT_TOPIC, "partition": 1}])
async def test_produces_alert_event_if_messaging_provided(datadog_alert):
    consumer = FakeAIOKafkaConsumer()
    await consumer.start()
    consumer.subscribe([settings.KAFKA_ALERT_TOPIC])

    fixed_time = datetime(2025, 4, 30, 12, 0, 0)
    controller = AlertController(messaging=FakeKafkaRepository())
    await controller.process_alert(datadog_alert, received_at=fixed_time)

    message = await consumer.getone()

    raw_json = message.value.decode("utf-8")
    kafka_msg = AlertKafkaMessage.model_validate_json(raw_json)

    alert_domain = datadog_alert.to_domain(received_at=fixed_time)
    expected = AlertKafkaMessage.from_domain(alert_domain)

    assert message is not None
    assert kafka_msg == expected
    assert message.key.decode("utf-8") == expected.fingerprint
    # assert message.topic == "mocked_alerts_topic"
