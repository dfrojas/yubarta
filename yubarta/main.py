from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from yubarta.infra.db.initialization import init_database
from yubarta.infra.messaging.initialization import init_kafka
from yubarta.infra.messaging.kafka import producer
from yubarta.ingestion.router import router as ingestion_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    app.include_router(ingestion_router)

    db = await init_database()
    app.state.db = db

    kafka_admin = await init_kafka()
    app.state.kafka_admin = kafka_admin

    yield

    await producer.stop()
    await app.state.db.close()


app = FastAPI(lifespan=lifespan)
