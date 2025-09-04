from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer

from backend.app.api.management.schemas.auth_keys import (
    AuthKeyCreate,
    AuthKeyResponse,
    AuthKeyUpdate,
)
from backend.app.core.security import get_current_user
from backend.app.services.auth_service import AuthService

router = APIRouter()
security = HTTPBearer()


async def get_auth_service() -> AuthService:
    service = AuthService()
    return service


@router.post(
    "/auth_keys", response_model=AuthKeyResponse, status_code=status.HTTP_201_CREATED
)
async def create_auth_key(
    key_create: AuthKeyCreate,
    auth_service: AuthService = Depends(get_auth_service),
    current_user: bool = Depends(
        get_current_user
    ),  # Protect this endpoint with get_current_user
):
    existing_keys = await auth_service.get_keys()
    if any(key.alias == key_create.alias for key in existing_keys):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Alias already exists."
        )

    new_key = await auth_service.create_key(key_create)
    return AuthKeyResponse(
        api_key=new_key.api_key, alias=new_key.alias, call_count=new_key.call_count
    )


@router.get("/auth_keys", response_model=List[AuthKeyResponse])
async def get_auth_keys(
    auth_service: AuthService = Depends(get_auth_service),
    current_user: bool = Depends(
        get_current_user
    ),  # Protect this endpoint with get_current_user
):
    keys = await auth_service.get_keys()
    return [
        AuthKeyResponse(api_key=key.api_key, alias=key.alias, call_count=key.call_count)
        for key in keys
    ]


@router.put("/auth_keys/{api_key}", response_model=AuthKeyResponse)
async def update_auth_key_alias(
    api_key: str,
    key_update: AuthKeyUpdate,
    auth_service: AuthService = Depends(get_auth_service),
    current_user: bool = Depends(
        get_current_user
    ),  # Protect this endpoint with get_current_user
):
    updated_key = await auth_service.update_key_alias(api_key, key_update.alias)
    if not updated_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Auth key not found."
        )
    return AuthKeyResponse(
        api_key=updated_key.api_key,
        alias=updated_key.alias,
        call_count=updated_key.call_count,
    )


@router.delete("/auth_keys/{api_key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_auth_key(
    api_key: str,
    auth_service: AuthService = Depends(get_auth_service),
    current_user: bool = Depends(
        get_current_user
    ),  # Protect this endpoint with get_current_user
):
    deleted = await auth_service.delete_key(api_key)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Auth key not found."
        )
    return
