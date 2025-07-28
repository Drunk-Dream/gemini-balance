import asyncio
import random
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, Optional, Union

import httpx
from app.core.config import settings
from app.core.logging import app_logger, setup_debug_logger
from app.services.redis_key_manager import redis_key_manager as key_manager
from fastapi import HTTPException
from starlette.responses import StreamingResponse

logger = app_logger


class ApiService(ABC):
    """
    Base class for API services, handling common logic like HTTP client,
    API key management, retry mechanisms, and streaming responses.
    """

    def __init__(self, base_url: str, service_name: str):
        self.base_url = base_url
        self.service_name = service_name
        self.client = httpx.AsyncClient(base_url=self.base_url)
        self.max_retries = len(settings.GOOGLE_API_KEYS or []) or 1
        if self.max_retries == 0:
            raise ValueError("No Google API keys configured.")
        self._current_api_key: Optional[str] = None  # 初始化 _current_api_key

        self.debug_logger = setup_debug_logger(f"{service_name}_debug_logger")

    async def _stream_response(
        self, response: httpx.Response
    ) -> AsyncGenerator[str, None]:
        """
        Asynchronously yields decoded chunks from an httpx.Response stream.
        Logs each chunk if debug logging is enabled.
        """
        async for chunk in response.aiter_bytes():
            decoded_chunk = chunk.decode("utf-8")
            if settings.DEBUG_LOG_ENABLED:
                self.debug_logger.debug(f"Stream chunk: {decoded_chunk}")
            yield decoded_chunk

    @abstractmethod
    def _get_api_url(self, *args, **kwargs) -> str:
        """
        Abstract method to get the specific API endpoint URL.
        Must be implemented by subclasses.
        """
        pass

    @abstractmethod
    def _prepare_headers(self, api_key: str) -> Dict[str, str]:
        """
        Abstract method to prepare request headers, including API key.
        Must be implemented by subclasses.
        """
        pass

    async def _send_request(
        self,
        method: str,
        url: str,
        request_data: Any,
        stream: bool,
        params: Dict[str, str],
        model_id: Optional[str] = None,  # 新增 model_id 参数
    ) -> Union[Dict[str, Any], StreamingResponse]:
        """
        Handles sending the HTTP request, including API key management and retries.
        """
        last_exception = None
        for attempt in range(self.max_retries):
            api_key = await key_manager.get_next_key()
            self._current_api_key = api_key  # 存储当前使用的 key
            if not api_key:
                logger.error(
                    f"Attempt {attempt + 1}/{self.max_retries}: "
                    "No available API keys in the pool."
                )
                await key_manager.repair_redis_database()
                last_exception = HTTPException(
                    status_code=503, detail="No available API keys."
                )
                continue

            key_identifier = key_manager._get_key_identifier(api_key)
            logger.info(
                f"Attempt {attempt + 1}/{self.max_retries}: "
                f"Using API key {key_identifier} for {self.service_name}, stream={stream}"
            )

            headers = self._prepare_headers(api_key)

            try:
                if settings.DEBUG_LOG_ENABLED:
                    self.debug_logger.debug(
                        "Request to %s API with key %s: %s",
                        self.service_name,
                        key_identifier,
                        request_data.model_dump_json(by_alias=True, exclude_unset=True),
                    )

                response = await self.client.request(
                    method,
                    url,
                    json=request_data.model_dump(by_alias=True, exclude_unset=True),
                    headers=headers,
                    params=params,
                    timeout=60.0,
                )
                response.raise_for_status()

                # 请求成功，标记 key 成功
                await key_manager.mark_key_success(key_identifier)
                # 记录成功调用的 key 和 model 用量
                if model_id:
                    await key_manager.record_usage(key_identifier, model_id)

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
                        self.debug_logger.debug(
                            "Response from %s API with key %s: %s",
                            self.service_name,
                            key_identifier,
                            response_json,
                        )
                    logger.info(f"Request with key {key_identifier} succeeded.")
                    return response_json

            except httpx.HTTPStatusError as e:
                last_exception = e
                if e.response.status_code in [401, 403]:
                    error_type = "auth_error"
                elif e.response.status_code == 429:
                    error_type = "rate_limit_error"
                else:
                    error_type = "other_http_error"

                logger.warning(
                    f"API Key {key_identifier} failed with status {e.response.status_code}. "
                    f"Deactivating it. Attempt {attempt + 1}/{self.max_retries}."
                )
                await key_manager.deactivate_key(key_identifier, error_type)

                if e.response.status_code == 429:
                    retry_after = e.response.headers.get("Retry-After")
                    if retry_after:
                        try:
                            wait_time = int(retry_after) + random.randint(1, 9)
                            logger.warning(
                                f"Rate limit hit for API Key {key_identifier}. "
                                f"Retrying after Retry-After header: {wait_time} seconds."  # noqa:E501
                            )
                        except ValueError:
                            wait_time = (
                                settings.RATE_LIMIT_DEFAULT_WAIT_SECONDS
                                + random.randint(1, 9)
                            )
                            logger.warning(
                                f"Rate limit hit for API Key {key_identifier}. "
                                f"Invalid Retry-After header. Waiting {wait_time} seconds before retrying."  # noqa:E501
                            )
                    else:
                        wait_time = (
                            settings.RATE_LIMIT_DEFAULT_WAIT_SECONDS
                            + random.randint(1, 9)
                        )
                        logger.warning(
                            f"Rate limit hit for API Key {key_identifier}. "
                            f"No Retry-After header. Waiting {wait_time} seconds before retrying."  # noqa:E501
                        )
                    await asyncio.sleep(wait_time)

                continue
            except httpx.RequestError as e:
                last_exception = e
                logger.error(
                    f"Request error with key {key_identifier}: {e}. "
                    f"Attempt {attempt + 1}/{self.max_retries}. Deactivating and retrying..."
                )
                await key_manager.deactivate_key(key_identifier, "request_error")
                continue
            except Exception as e:
                last_exception = e
                logger.critical(
                    f"An unexpected error occurred with key {key_identifier}: {e}. No retry."  # noqa:E501
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
                    detail=f"All API key attempts failed. Last error: {str(last_exception)}",  # noqa:E501
                )
        else:
            raise HTTPException(
                status_code=500, detail="No API keys were available or processed."
            )
