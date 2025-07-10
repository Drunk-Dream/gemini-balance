import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Union

import httpx
from fastapi import HTTPException
from starlette.responses import StreamingResponse

from app.api.v1beta.schemas.gemini import Request as GeminiRequest
from app.core.config import settings

# from app.core.logging import transaction_logger  # Import the new transaction logger

logger = logging.getLogger(__name__)

# 创建一个单独的调试日志记录器 (Existing debug logger setup)
debug_logger = logging.getLogger("gemini_debug_logger")
debug_logger.setLevel(logging.DEBUG)
debug_logger.propagate = False  # 阻止日志传播到根记录器

if settings.DEBUG_LOG_ENABLED:
    log_file_path = Path(settings.DEBUG_LOG_FILE)
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_file_path, maxBytes=10 * 1024 * 1024, backupCount=5
    )
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    debug_logger.addHandler(file_handler)


class GeminiService:
    def __init__(self):
        self.api_key = settings.GOOGLE_API_KEY
        self.base_url = settings.GEMINI_API_BASE_URL
        self.client = httpx.AsyncClient(base_url=self.base_url)

    async def _stream_response(
        self, response: httpx.Response
    ) -> AsyncGenerator[str, None]:
        async for chunk in response.aiter_bytes():
            decoded_chunk = chunk.decode("utf-8")
            # transaction_logger.info(f"STREAM_CHUNK: {decoded_chunk}")
            if settings.DEBUG_LOG_ENABLED:
                debug_logger.debug(f"Stream chunk: {decoded_chunk}")
            yield decoded_chunk

    async def generate_content(
        self, model_id: str, request_data: GeminiRequest, stream: bool = False
    ) -> Union[Dict[str, Any], StreamingResponse]:
        action = "streamGenerateContent" if stream else "generateContent"
        url = f"/v1beta/models/{model_id}:{action}"
        headers = {"Content-Type": "application/json", "x-goog-api-key": self.api_key}
        params = {"alt": "sse"} if stream else {"alt": "json"}

        try:
            logger.info(
                f"Forwarding request to Gemini API: {url}"
                f" with model {model_id}, stream={stream}"
            )

            # Log the full request payload unconditionally
            # transaction_logger.info(
            #     "REQUEST: "
            #     f"{request_data.model_dump_json(by_alias=True, exclude_unset=True)}"
            # )
            if settings.DEBUG_LOG_ENABLED:
                debug_logger.debug(
                    "Request to Gemini API: %s",
                    request_data.model_dump_json(by_alias=True, exclude_unset=True),
                )

            response = await self.client.post(
                url,
                json=request_data.model_dump(by_alias=True, exclude_unset=True),
                headers=headers,
                params=params,
                timeout=60.0,
            )
            response.raise_for_status()

            if stream:
                return StreamingResponse(
                    self._stream_response(response), media_type="application/json"
                )
            else:
                response_json = response.json()
                # Log the full response payload unconditionally
                # transaction_logger.info(f"RESPONSE: {response_json}")
                if settings.DEBUG_LOG_ENABLED:
                    debug_logger.debug(f"Response from Gemini API: {response_json}")
                return response_json
        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
            )
            # Log error response unconditionally
            # transaction_logger.error(
            #     f"ERROR_RESPONSE: {e.response.status_code} - {e.response.text}"
            # )
            if settings.DEBUG_LOG_ENABLED:
                debug_logger.error(
                    "HTTP error response: %s - %s",
                    e.response.status_code,
                    e.response.text,
                )
            raise HTTPException(
                status_code=e.response.status_code, detail=e.response.text
            )
        except httpx.RequestError as e:
            logger.error(f"Request error occurred: {e}")
            # Log request error unconditionally
            # transaction_logger.error(f"REQUEST_ERROR: {e}")
            if settings.DEBUG_LOG_ENABLED:
                debug_logger.error(f"Request error: {e}")
            raise HTTPException(status_code=500, detail=f"Request error: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            # Log unexpected error unconditionally
            # transaction_logger.error(f"UNEXPECTED_ERROR: {e}")
            if settings.DEBUG_LOG_ENABLED:
                debug_logger.error(f"Unexpected error: {e}")
            raise HTTPException(
                status_code=500, detail=f"An unexpected error occurred: {e}"
            )
