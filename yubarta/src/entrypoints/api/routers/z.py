from fastapi import APIRouter
from fastapi.responses import Response

router = APIRouter()


@router.get("/")
def home():
    whale_ascii = """
             .
            ":"
          ___:____     |"\/"|
        ,'        `.    \  /
        |  O        \___/  |
    ~^~^~^~^~^~^~^~^~^~^~^~^~
    """
    return Response(content=whale_ascii, media_type="text/plain", headers={"Content-Type": "text/plain; charset=utf-8"})


@router.get("/healthz")
async def health_check():
    return {"status": "healthy"}
