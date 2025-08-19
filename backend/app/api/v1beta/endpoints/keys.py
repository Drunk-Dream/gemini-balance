from app.api.v1beta.schemas.keys import (
    AddKeyRequest,
    BulkKeyOperationResponse,
    KeyOperationResponse,
)
from app.core.config import settings
from app.core.logging import app_logger
from app.core.security import get_current_user
from app.services.key_managers import get_key_manager
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter()
key_manager = get_key_manager(settings)


@router.post(
    "/keys",
    response_model=BulkKeyOperationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_keys(
    request: AddKeyRequest, current_user: str = Depends(get_current_user)
):
    """
    Add one or more new API keys.
    """
    added_keys = []
    for api_key in request.api_keys:
        try:
            key_identifier = await key_manager.add_key(api_key)
            added_keys.append(key_identifier)
        except Exception as e:
            app_logger.error(f"Failed to add key: {api_key[:5]}... - {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to add key: {e}",
            )
    return BulkKeyOperationResponse(
        message="Keys added successfully", details=added_keys
    )


@router.delete(
    "/keys/{key_identifier}",
    response_model=KeyOperationResponse,
    status_code=status.HTTP_200_OK,
)
async def delete_key(
    key_identifier: str, current_user: str = Depends(get_current_user)
):
    """
    Delete a specific API key by its identifier.
    """
    try:
        await key_manager.delete_key(key_identifier)
        return KeyOperationResponse(
            message=f"Key '{key_identifier}' deleted successfully",
            key_identifier=key_identifier,
        )
    except Exception as e:
        app_logger.error(f"Failed to delete key '{key_identifier}': {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete key '{key_identifier}': {e}",
        )


@router.post(
    "/keys/{key_identifier}/reset",
    response_model=KeyOperationResponse,
    status_code=status.HTTP_200_OK,
)
async def reset_single_key_state(
    key_identifier: str, current_user: str = Depends(get_current_user)
):
    """
    Reset the state of a specific API key.
    """
    try:
        await key_manager.reset_key_state(key_identifier)
        return KeyOperationResponse(
            message=f"State for key '{key_identifier}' reset successfully",
            key_identifier=key_identifier,
        )
    except Exception as e:
        app_logger.error(f"Failed to reset state for key '{key_identifier}': {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to reset state for key '{key_identifier}': {e}",
        )


@router.post(
    "/keys/reset",
    response_model=BulkKeyOperationResponse,
    status_code=status.HTTP_200_OK,
)
async def reset_all_keys_state(current_user: str = Depends(get_current_user)):
    """
    Reset the state of all API keys.
    """
    try:
        await key_manager.reset_all_key_states()
        return BulkKeyOperationResponse(
            message="State for all keys reset successfully", details=[]
        )
    except Exception as e:
        app_logger.error(f"Failed to reset all keys state: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to reset all keys state: {e}",
        )
