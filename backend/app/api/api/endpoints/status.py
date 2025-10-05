from fastapi import APIRouter, Depends

from backend.app.core.security import get_current_user
from backend.app.services.key_managers.key_state_manager import KeyStateManager
from backend.app.services.request_logs.request_log_manager import RequestLogManager

router = APIRouter()


@router.get("/status/keys", summary="获取所有 API Key 的状态和用量信息")
async def get_api_key_status(
    current_user: bool = Depends(get_current_user),
    key_manager: KeyStateManager = Depends(KeyStateManager),
    request_log_manager: RequestLogManager = Depends(RequestLogManager),
):  # 保护此端点
    """
    返回所有配置的 API Key 的详细状态列表，包括：
    - key_identifier: API Key 的部分标识（末尾四位），用于安全展示。
    - status: Key 的当前状态（"active" 或 "cooling_down"）。
    - cool_down_seconds_remaining: 如果 Key 处于冷却状态，剩余的冷却秒数。
    - daily_usage: 一个字典，显示该 Key 下每个模型在当日的用量。
    - failure_count: 该 Key 连续失败的次数。
    - cool_down_entry_count: 该 Key 进入冷却状态的总次数。
    - current_cool_down_seconds: 当前 Key 的冷却时长。
    """
    key_states = await key_manager.get_all_key_states()
    daily_usage_stats = await request_log_manager.get_daily_model_usage_stats()
    for key_state in key_states:
        key_state.daily_usage = daily_usage_stats.get(key_state.key_identifier, {})
    return {"keys": key_states}
