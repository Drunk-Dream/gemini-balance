from typing import List

from pydantic import BaseModel


class AddKeyRequest(BaseModel):
    api_keys: List[str]


class KeyOperationResponse(BaseModel):
    message: str
    key_identifier: str


class BulkKeyOperationResponse(BaseModel):
    message: str
    details: List[str]


class KeyStatus(BaseModel):
    key_identifier: str
    key_brief: str
    status: str
    cool_down_seconds_remaining: float
    failure_count: int
    cool_down_entry_count: int
    current_cool_down_seconds: int


class KeyStatusResponse(BaseModel):
    keys: List[KeyStatus]
    total_keys_count: int
    in_use_keys_count: int
    cooled_down_keys_count: int
    available_keys_count: int
