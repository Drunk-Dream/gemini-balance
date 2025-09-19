from pydantic import BaseModel, Field


class AuthKeyCreate(BaseModel):
    """Schema for creating a new authentication key."""

    alias: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="A user-friendly name for the key.",
    )


class AuthKeyUpdate(BaseModel):
    """Schema for updating an authentication key's alias."""

    alias: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="The new user-friendly name for the key.",
    )


class AuthKeyResponse(BaseModel):
    """Schema for returning an authentication key to the client."""

    api_key: str
    alias: str
    call_count: int

    class Config:
        from_attributes = True
