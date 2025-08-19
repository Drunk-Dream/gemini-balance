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
