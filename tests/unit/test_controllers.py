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
        controller = AlertController()
        await controller.process_alert(datadog_alert)
    assert str(e.value) == "No storage or messaging provider configured"


async def test_stores_alert_if_storage_provided(datadog_alert):
    storage = FakeDbRepository()
    controller = AlertController(storage=storage)

    alert_domain = datadog_alert.to_domain(received_at=datetime.utcnow())
    processed_alert = await controller.process_alert(alert_domain)
    assert storage.alerts[processed_alert.fingerprint] == processed_alert


# The topic name must be explicitly hardcoded in the asetup_kafka decorator rather than using
# settings.KAFKA_ALERT_TOPIC because the decorator runs during module import, before the
# patch_settings fixture in conftest.py can override environment variables. If we used
# settings.KAFKA_ALERT_TOPIC here, it would create a topic with the default name ("alerts")
# but later try to produce to "mocked_alerts_topic", causing "partition does not exist" errors.
@asetup_kafka(topics=[{"topic": "mocked_alerts_topic", "partition": 3}], clean=True)
async def test_produces_alert_event_if_messaging_provided(datadog_alert):
    consumer = FakeAIOKafkaConsumer()
    await consumer.start()
    consumer.subscribe([settings.KAFKA_ALERT_TOPIC])

    fixed_time = datetime(2025, 4, 30, 12, 0, 0)
    alert_domain = datadog_alert.to_domain(received_at=fixed_time)

    controller = AlertController(messaging=FakeKafkaRepository())
    await controller.process_alert(alert_domain)

    message = await consumer.getone()

    raw_json = message.value.decode("utf-8")
    kafka_msg = AlertKafkaMessage.model_validate_json(raw_json)

    expected = AlertKafkaMessage.from_domain(alert_domain)

    assert message is not None
    assert kafka_msg == expected
    assert message.key.decode("utf-8") == expected.fingerprint
    assert message.topic == "mocked_alerts_topic"
