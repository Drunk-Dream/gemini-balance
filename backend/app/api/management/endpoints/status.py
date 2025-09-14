from fastapi import APIRouter, Depends

from backend.app.core.security import get_current_user
from backend.app.services.key_managers import get_key_manager
from backend.app.services.key_managers.key_state_manager import KeyStateManager

router = APIRouter()


@router.get("/status/keys", summary="获取所有 API Key 的状态和用量信息")
async def get_api_key_status(
    current_user: bool = Depends(get_current_user),
    key_manager: KeyStateManager = Depends(get_key_manager),
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
    key_states = await key_manager.get_key_states()
    return {"keys": key_states}
