"""Bearer-token authentication for the Control API.

Auth is a single static bearer token for now. The token value comes from the
environment variable named by ``api.token_from_env``; the name is configuration,
the secret is never written to disk. Multi-user support should replace this with
JWT: a login endpoint, ``OAuth2PasswordBearer``, and per-user tokens.
"""

from __future__ import annotations

import hmac
import os
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from yubarta.config.settings import AppConfig

bearer_scheme = HTTPBearer(auto_error=False)


def resolve_api_token(config: AppConfig) -> str | None:
    """Resolve the expected token once at startup. Fail closed on misconfiguration."""
    env_name = config.api.token_from_env
    if not env_name:
        return None
    token = os.environ.get(env_name, "")
    if not token:
        raise RuntimeError(f"API auth is enabled via '{env_name}' but that variable is empty or unset")
    return token


def require_bearer(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> None:
    """Router-level dependency. No token configured means auth is disabled."""
    expected = request.app.state.api_token
    if not expected:
        return
    provided = credentials.credentials if credentials is not None else ""
    if not hmac.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
