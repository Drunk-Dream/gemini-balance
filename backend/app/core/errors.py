from enum import Enum


class ErrorType(Enum):
    AUTH_ERROR = ("auth_error", True)
    RATE_LIMIT_ERROR = ("rate_limit_error", True)
    UNEXPECTED_ERROR = ("unexpected_error", True)
    OTHER_HTTP_ERROR = ("other_http_error", False)
    REQUEST_ERROR = ("request_error", False)
    USE_TIMEOUT_ERROR = ("use_timeout_error", False)
    STREAMING_COMPLETION_ERROR = ("streaming_completion_error", False)

    def __init__(self, value: str, should_cool_down: bool):
        self._value_: str = value
        self.should_cool_down = should_cool_down

    @classmethod
    def from_str(cls, error_str: str) -> "ErrorType":
        for error_type in cls:
            if error_type.value == error_str:
                return error_type
        raise ValueError(f"Unknown error type: {error_str}")


class StreamingCompletionError(Exception):
    """
    Custom exception for streaming requests that finish without a STOP signal.
    """

    pass
