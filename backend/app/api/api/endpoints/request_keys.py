from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.api.api.schemas.request_keys import (
    AddKeyRequest,
    BulkKeyOperationResponse,
    KeyOperationResponse,
    KeyStatusResponse,
)
from backend.app.core.logging import app_logger
from backend.app.core.security import get_current_user
from backend.app.services.request_key_manager.key_state_manager import KeyStateManager
from backend.app.services.request_logs.request_log_manager import RequestLogManager

router = APIRouter()


@router.post(
    "/keys",
    response_model=BulkKeyOperationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_keys(
    request: AddKeyRequest,
    current_user: str = Depends(get_current_user),
    key_manager: KeyStateManager = Depends(KeyStateManager),
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
    key_identifier: str,
    current_user: str = Depends(get_current_user),
    key_manager: KeyStateManager = Depends(KeyStateManager),
):
    """
    Delete a specific API key by its identifier.
    """
    try:
        await key_manager.delete_key(key_identifier)
        return KeyOperationResponse(
            message=f"Key {key_identifier} deleted successfully",
            key_identifier=key_identifier,
        )
    except Exception as e:
        app_logger.error(f"Failed to delete key {key_identifier}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete key {key_identifier}: {e}",
        )


@router.post(
    "/keys/{key_identifier}/reset",
    response_model=KeyOperationResponse,
    status_code=status.HTTP_200_OK,
)
async def reset_single_key_state(
    key_identifier: str,
    current_user: str = Depends(get_current_user),
    key_manager: KeyStateManager = Depends(KeyStateManager),
):
    """
    Reset the state of a specific API key.
    """
    try:
        await key_manager.reset_key_state(key_identifier)
        return KeyOperationResponse(
            message=f"State for key {key_identifier} reset successfully",
            key_identifier=key_identifier,
        )
    except Exception as e:
        app_logger.error(f"Failed to reset state for key {key_identifier}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to reset state for key {key_identifier}: {e}",
        )


@router.post(
    "/keys/reset",
    response_model=BulkKeyOperationResponse,
    status_code=status.HTTP_200_OK,
)
async def reset_all_keys_state(
    current_user: str = Depends(get_current_user),
    key_manager: KeyStateManager = Depends(KeyStateManager),
):
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


@router.get("/keys/status", summary="获取所有 API Key 的状态，包括总数、使用中、冷却中和可用 Key 的数量")
async def get_api_key_status(
    current_user: bool = Depends(get_current_user),
    key_manager: KeyStateManager = Depends(KeyStateManager),
    request_log_manager: RequestLogManager = Depends(RequestLogManager),
) -> KeyStatusResponse:  # 保护此端点
    """
    返回所有配置的 API Key 的详细状态列表，包括：
    - key_identifier: API Key 的部分标识（末尾四位），用于安全展示。
    - key_brief: API Key 的简要描述。
    - status: Key 的当前状态（"active" 或 "cooling_down"）。
    - cool_down_seconds_remaining: 如果 Key 处于冷却状态，剩余的冷却秒数。
    - failure_count: 该 Key 连续失败的次数。
    - cool_down_entry_count: 该 Key 进入冷却状态的总次数。
    - current_cool_down_seconds: 当前 Key 的冷却时长。
    - is_in_use: 表示 Key 当前是否正在被使用。
    """
    return await key_manager.get_all_key_status()
