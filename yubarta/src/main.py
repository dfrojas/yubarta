import uvicorn
from .api.api_server import app

def start_server():
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    start_server()
