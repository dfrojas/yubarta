from fastapi import FastAPI
from contextlib import asynccontextmanager
from yubarta.drivers.db.initialization import init_database
from yubarta.drivers.db.orm import start_mappers
from yubarta.entrypoints.api_server.v1.router import router as v1_router
from sqlalchemy.ext.asyncio import AsyncSession


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.include_router(v1_router)
    db = await init_database()
    app.state.db = db
    yield
    # Cleanup could go here if needed

app = FastAPI(lifespan=lifespan)
