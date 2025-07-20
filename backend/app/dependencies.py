from typing import Annotated

from app.services.key_manager import KeyManager
from fastapi import Depends, Request


def get_key_manager(request: Request) -> KeyManager:
    return request.app.state.key_manager


KeyManagerDep = Annotated[KeyManager, Depends(get_key_manager)]
