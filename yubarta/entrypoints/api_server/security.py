import hmac
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from yubarta.entrypoints.api_server.dependencies import RuntimeDep


def require_bearer(runtime: RuntimeDep,
                   credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(HTTPBearer(auto_error=False))]) -> None:
    token = runtime.config.api.token
    if token is None:
        return
    if credentials is None or not hmac.compare_digest(credentials.credentials.encode(), token.get_secret_value().encode()):
        raise HTTPException(401, "Invalid API token", headers={"WWW-Authenticate": "Bearer"})
