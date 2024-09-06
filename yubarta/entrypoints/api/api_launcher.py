import uvicorn
from fastapi import FastAPI

from .v1.routers import deploy_router, z_router

app = FastAPI()

app.include_router(deploy_router)
app.include_router(z_router)


def start_api():
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    start_api()
