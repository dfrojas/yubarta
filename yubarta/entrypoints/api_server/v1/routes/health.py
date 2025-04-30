from fastapi import APIRouter, Response
from typing import Dict

router = APIRouter(prefix="/z", tags=["health"])


@router.get("/whale")
def home() -> Response:
    whale_ascii = r"""
             .
            ":"
          ___:____     |"\/"|
        ,'        `.    \  /
        |  O        \___/  |
    ~^~^~^~^~^~^~^~^~^~^~^~^~
    """
    return Response(
        content=whale_ascii,
        media_type="text/plain",
        headers={"Content-Type": "text/plain; charset=utf-8"},
    )


@router.get("/healthz")
async def health_check() -> Dict[str, str]:
    return {"status": "healthy"}
