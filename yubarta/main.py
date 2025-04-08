from fastapi import FastAPI
from contextlib import asynccontextmanager
from yubarta.drivers.db.initialization import init_database
from yubarta.drivers.db.orm import start_mappers
from yubarta.entrypoints.api_server.v1.router import router as v1_router
from sqlalchemy.ext.asyncio import AsyncSession
from yubarta.drivers.messaging.kafka import producer
from yubarta.scripts.create_kafka_topics import create_topics


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.include_router(v1_router)
    # Initialize database
    db = await init_database()
    app.state.db = db
    
    # Initialize Kafka
    await create_topics()
    await producer.start()
    
    yield
    
    # Cleanup
    # await producer.stop()

app = FastAPI(lifespan=lifespan)
