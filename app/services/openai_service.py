import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Union

import httpx
from fastapi import HTTPException
from starlette.responses import StreamingResponse

from app.api.openai.schemas.chat import ChatCompletionRequest
from app.core.config import settings
from app.core.logging import app_logger
from app.services.key_manager import key_manager

logger = app_logger

debug_logger = logging.getLogger("openai_debug_logger")
debug_logger.setLevel(logging.DEBUG)
debug_logger.propagate = False

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


class OpenAIService:
    def __init__(self):
        self.base_url = settings.OPENAI_API_BASE_URL
        self.client = httpx.AsyncClient(base_url=self.base_url)
        self.max_retries = len(settings.GOOGLE_API_KEYS or []) or 1
        if self.max_retries == 0:
            raise ValueError("No Google API keys configured.")

    async def _stream_response(
        self, response: httpx.Response
    ) -> AsyncGenerator[str, None]:
        async for chunk in response.aiter_bytes():
            decoded_chunk = chunk.decode("utf-8")
            if settings.DEBUG_LOG_ENABLED:
                debug_logger.debug(f"Stream chunk: {decoded_chunk}")
            yield decoded_chunk

    async def create_chat_completion(
        self, request_data: ChatCompletionRequest
    ) -> Union[Dict[str, Any], StreamingResponse]:
        url = "/v1beta/openai/chat/completions"
        stream = request_data.stream
        params = {"alt": "sse"} if stream else {"alt": "json"}

        last_exception = None
        for attempt in range(self.max_retries):
            api_key = await key_manager.get_next_key()
            if not api_key:
                logger.error(
                    f"Attempt {attempt + 1}/{self.max_retries}: "
                    "No available API keys in the pool."
                )
                last_exception = HTTPException(
                    status_code=503, detail="No available API keys."
                )
                break

            key_identifier = f"...{api_key[-4:]}"
            logger.info(
                f"Attempt {attempt + 1}/{self.max_retries}: "
                f"Using API key {key_identifier} for OpenAI chat completion, stream={stream}"
            )

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            }

            try:
                if settings.DEBUG_LOG_ENABLED:
                    debug_logger.debug(
                        "Request to OpenAI compatibility API with key %s: %s",
                        key_identifier,
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
                    logger.info(
                        f"Request with key {key_identifier} succeeded (streaming)."
                    )
                    return StreamingResponse(
                        self._stream_response(response), media_type="text/event-stream"
                    )
                else:
                    response_json = response.json()
                    if settings.DEBUG_LOG_ENABLED:
                        debug_logger.debug(
                            "Response from OpenAI compatibility API with key %s: %s",
                            key_identifier,
                            response_json,
                        )
                    logger.info(f"Request with key {key_identifier} succeeded.")
                    return response_json

            except httpx.HTTPStatusError as e:
                last_exception = e
                if e.response.status_code in [401, 403, 429]:
                    logger.warning(
                        f"API Key {key_identifier} failed with status {e.response.status_code}. "
                        f"Deactivating it for {settings.API_KEY_COOL_DOWN_SECONDS} seconds. "
                        f"Attempt {attempt + 1}/{self.max_retries}."
                    )
                    await key_manager.deactivate_key(api_key)
                    continue
                else:
                    logger.error(
                        f"HTTP error with key {key_identifier}: "
                        f"{e.response.status_code} - {e.response.text}. No retry."
                    )
                    raise HTTPException(
                        status_code=e.response.status_code, detail=e.response.text
                    )
            except httpx.RequestError as e:
                last_exception = e
                logger.error(
                    f"Request error with key {key_identifier}: {e}. "
                    f"Attempt {attempt + 1}/{self.max_retries}. Retrying..."
                )
                continue
            except Exception as e:
                last_exception = e
                logger.critical(
                    f"An unexpected error occurred with key {key_identifier}: {e}. No retry."
                )
                raise HTTPException(
                    status_code=500, detail=f"An unexpected error occurred: {e}"
                )

        if last_exception:
            logger.critical(
                f"All {self.max_retries} API key attempts failed. "
                f"Last error: {last_exception}"
            )
            if isinstance(last_exception, HTTPException):
                raise last_exception
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"All API key attempts failed. Last error: {str(last_exception)}",
                )
        else:
            raise HTTPException(
                status_code=500, detail="No API keys were available or processed."
            )
