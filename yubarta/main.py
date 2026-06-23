from fastapi import FastAPI

from yubarta.ingestion.router import router as ingestion_router

app = FastAPI()
app.include_router(ingestion_router)
