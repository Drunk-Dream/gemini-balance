import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Union

import httpx
from fastapi import HTTPException
from starlette.responses import StreamingResponse

from app.api.v1beta.schemas.gemini import Request as GeminiRequest
from app.core.config import settings
from app.core.logging import app_logger  # 导入 app_logger
from app.services.key_manager import key_manager  # 导入 KeyManager 实例

logger = app_logger  # 使用主应用日志记录器

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
        self.base_url = settings.GEMINI_API_BASE_URL
        self.client = httpx.AsyncClient(base_url=self.base_url)
        # 最大重试次数，可以根据 KEY 数量调整，例如每个 KEY 尝试一次
        # 确保 settings.GOOGLE_API_KEYS 不为 None，如果为 None 则视为空列表
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

    async def generate_content(
        self, model_id: str, request_data: GeminiRequest, stream: bool = False
    ) -> Union[Dict[str, Any], StreamingResponse]:
        action = "streamGenerateContent" if stream else "generateContent"
        url = f"/v1beta/models/{model_id}:{action}"
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
                break  # 没有可用的 key，直接退出重试循环

            key_identifier = f"...{api_key[-4:]}"
            logger.info(
                f"Attempt {attempt + 1}/{self.max_retries}: "
                f"Using API key {key_identifier} for model {model_id}, stream={stream}"
            )

            headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}

            try:
                if settings.DEBUG_LOG_ENABLED:
                    debug_logger.debug(
                        "Request to Gemini API with key %s: %s",
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
                        self._stream_response(response), media_type="application/json"
                    )
                else:
                    response_json = response.json()
                    if settings.DEBUG_LOG_ENABLED:
                        debug_logger.debug(
                            "Response from Gemini API with key %s: %s",
                            key_identifier,
                            response_json,
                        )
                    logger.info(f"Request with key {key_identifier} succeeded.")
                    return response_json

            except httpx.HTTPStatusError as e:
                last_exception = e
                if e.response.status_code in [401, 403, 429]:
                    logger.warning(
                        f"API Key {key_identifier} failed with status {e.response.status_code}. "  # noqa: E501
                        f"Deactivating it for {settings.API_KEY_COOL_DOWN_SECONDS} seconds. "  # noqa: E501
                        f"Attempt {attempt + 1}/{self.max_retries}."
                    )
                    await key_manager.deactivate_key(api_key)
                    continue  # 继续循环，尝试下一个 key
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
                    f"An unexpected error occurred with key {key_identifier}: {e}. No retry."  # noqa: E501
                )
                raise HTTPException(
                    status_code=500, detail=f"An unexpected error occurred: {e}"
                )

        # 如果所有重试都失败了，或者没有可用的 key
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
                    detail=f"All API key attempts failed. Last error: {str(last_exception)}",  # noqa: E501
                )
        else:
            # 这种情况理论上不应该发生，除非 max_retries 为 0 且没有 key
            raise HTTPException(
                status_code=500, detail="No API keys were available or processed."
            )
