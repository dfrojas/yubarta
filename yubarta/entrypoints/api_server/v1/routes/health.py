from fastapi import APIRouter, Response

router = APIRouter(prefix="/z", tags=["health"])


@router.get("/whale")
def home():
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
async def health_check():
    return {"status": "healthy"}
