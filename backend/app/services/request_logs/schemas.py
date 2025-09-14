from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RequestLog(BaseModel):
    """
    表示单个请求日志条目的 Pydantic 模型。
    """

    id: Optional[int] = Field(None, description="日志条目的唯一 ID，由数据库自动生成。")
    request_id: str = Field(..., description="请求的唯一 ID。")
    request_time: datetime = Field(..., description="请求发生的时间 (UTC)。")
    key_identifier: str = Field(..., description="用于请求的 API 密钥的标识符。")
    auth_key_alias: str = Field(..., description="用户认证密钥的别名。")
    model_name: str = Field(..., description="使用的模型名称。")
    is_success: bool = Field(..., description="请求是否成功。")

    class Config:
        from_attributes = True  # 允许从 ORM 模型创建 Pydantic 模型
