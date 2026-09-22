from typing import Annotated

from fastapi import Depends, Request

from yubarta.runtime import YubartaRuntime


def get_runtime(request: Request) -> YubartaRuntime:
    return request.app.state.runtime


type RuntimeDep = Annotated[YubartaRuntime, Depends(get_runtime)]
