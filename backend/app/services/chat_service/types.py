from pydantic import BaseModel


class RequestInfo(BaseModel):
    request_id: str
    model_id: str
    auth_key_alias: str = "anonymous"
    stream: bool
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
