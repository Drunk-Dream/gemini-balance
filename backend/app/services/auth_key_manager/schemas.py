import secrets
import string

from pydantic import BaseModel, Field


def generate_api_key(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


class AuthKey(BaseModel):
    """Represents an authentication key in the database."""

    api_key: str = Field(
        default_factory=generate_api_key, description="The authentication API key."
    )
    alias: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="A user-friendly name for the key.",
    )
