from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI

from yubarta.drivers.db.initialization import init_database
from yubarta.drivers.messaging.initialization import init_kafka
from yubarta.drivers.messaging.kafka import producer
from yubarta.entrypoints.api_server.v1.router import router as v1_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    app.include_router(v1_router)

    # Initialize database
    db = await init_database()
    app.state.db = db

    # Initialize Kafka
    kafka_admin = await init_kafka()
    app.state.kafka_admin = kafka_admin

    yield

    # Cleanup
    await producer.stop()
    await app.state.db.close()


app = FastAPI(lifespan=lifespan)
