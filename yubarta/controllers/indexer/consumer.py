import asyncio
import time
from aiokafka import AIOKafkaConsumer
from sqlalchemy.ext.asyncio import AsyncSession

async def indexer_consumer_worker(app):
    print("Indexer consumer worker started")
    consumer = AIOKafkaConsumer(
        "indexer",
        bootstrap_servers="kafka:9092",
        group_id="yubarta-indexer",
        enable_auto_commit=False,
    )
    await consumer.start()
    app.state.consumer_running = True
    try:
        while not app.state.stop_event.is_set():
            msgs = await consumer.getmany(timeout_ms=1000, max_records=100)
            if not msgs:
                continue

            # Flatten mensajes
            batch = []
            for tp, messages in msgs.items():
                for msg in messages:
                    batch.append(msg)

            # Persistir en BD
            async with AsyncSession(app.state.db_engine) as session:
                for msg in batch:
                    # Ejemplo de inserción simple (usando PK=event_id para idempotencia)
                    print(msg, "MENSAJE EN INDEXER CONSUMER")
                    # await session.execute(
                    #     "INSERT INTO alerts(event_id, payload) VALUES (:id, :payload) "
                    #     "ON CONFLICT (event_id) DO NOTHING",
                    #     {"id": msg.key.decode(), "payload": msg.value.decode()},
                    # )
                await session.commit()

            # Commit offsets después de persistir
            await consumer.commit()
            app.state.last_commit_ts = time.time()

    finally:
        app.state.consumer_running = False
        await consumer.stop()
