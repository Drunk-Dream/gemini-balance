import asyncio
import random
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, Optional, Union, cast

import httpx
from app.core.config import settings
from app.core.logging import app_logger, setup_debug_logger, transaction_logger
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

    async def _request_generator(
        self,
        method: str,
        url: str,
        request_data: Any,
        stream: bool,
        params: Dict[str, str],
        model_id: Optional[str] = None,
    ) -> AsyncGenerator[Union[str, Dict[str, Any]], None]:
        """
        A unified generator to handle both streaming and non-streaming requests.
        It manages API key rotation, retries, and error handling.
        """
        last_exception = None
        for attempt in range(self.max_retries):
            api_key = await key_manager.get_next_key()
            self._current_api_key = api_key
            if not api_key:
                logger.error(
                    f"Attempt {attempt + 1}/{self.max_retries}: No available API keys."
                )
                last_exception = HTTPException(
                    status_code=503, detail="No available API keys."
                )
                continue

            key_identifier = key_manager._get_key_identifier(api_key)
            logger.info(
                f"Attempt {attempt + 1}/{self.max_retries}: Using API key "
                f"{key_identifier} for {self.service_name}, stream={stream}"
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

                if stream:
                    async with self.client.stream(
                        method,
                        url,
                        json=request_data.model_dump(by_alias=True, exclude_unset=True),
                        headers=headers,
                        params=params,
                        timeout=120.0,
                    ) as response:
                        response.raise_for_status()
                        await key_manager.mark_key_success(key_identifier)
                        if model_id:
                            await key_manager.record_usage(key_identifier, model_id)
                        logger.info(
                            f"Streaming request with key {key_identifier} succeeded."
                        )
                        async for text_chunk in response.aiter_text():
                            transaction_logger.info(f"Stream chunk: {text_chunk}")
                            yield text_chunk
                        return
                else:
                    response = await self.client.request(
                        method,
                        url,
                        json=request_data.model_dump(by_alias=True, exclude_unset=True),
                        headers=headers,
                        params=params,
                        timeout=120.0,
                    )
                    response.raise_for_status()
                    await key_manager.mark_key_success(key_identifier)
                    if model_id:
                        await key_manager.record_usage(key_identifier, model_id)
                    response_json = response.json()
                    transaction_logger.info(
                        "Response from %s API with key %s: %s",
                        self.service_name,
                        key_identifier,
                        response_json,
                    )
                    logger.info(f"Request with key {key_identifier} succeeded.")
                    yield response_json
                    return

            except httpx.HTTPStatusError as e:
                last_exception = e
                error_type = "other_http_error"
                if e.response.status_code in [401, 403]:
                    error_type = "auth_error"
                elif e.response.status_code == 429:
                    error_type = "rate_limit_error"

                logger.warning(
                    f"API Key {key_identifier} failed with status {e.response.status_code}. "
                    f"Deactivating it. Attempt {attempt + 1}/{self.max_retries}."
                )
                await key_manager.deactivate_key(key_identifier, error_type)

                if e.response.status_code == 429:
                    retry_after = e.response.headers.get("Retry-After")
                    wait_time = settings.RATE_LIMIT_DEFAULT_WAIT_SECONDS
                    if retry_after:
                        try:
                            wait_time = int(retry_after)
                        except ValueError:
                            logger.warning("Invalid Retry-After header.")
                    wait_time += random.randint(1, 9)
                    logger.warning(
                        f"Rate limit hit. Retrying after {wait_time} seconds."
                    )
                    await asyncio.sleep(wait_time)
                continue
            except httpx.RequestError as e:
                last_exception = e
                logger.error(
                    f"Request error with key {key_identifier}: {e}. Deactivating and retrying..."
                )
                await key_manager.deactivate_key(key_identifier, "request_error")
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
                f"All {self.max_retries} API key attempts failed. Last error: {last_exception}"
            )
            if isinstance(last_exception, HTTPException):
                raise last_exception
            raise HTTPException(
                status_code=500,
                detail=f"All API key attempts failed. Last error: {str(last_exception)}",
            )
        raise HTTPException(
            status_code=500, detail="No API keys were available or processed."
        )

    async def _send_request(
        self,
        method: str,
        url: str,
        request_data: Any,
        stream: bool,
        params: Dict[str, str],
        model_id: Optional[str] = None,
    ) -> Union[Dict[str, Any], StreamingResponse]:
        """
        Handles sending the HTTP request by dispatching to the appropriate generator.
        """
        generator = self._request_generator(
            method=method,
            url=url,
            request_data=request_data,
            stream=stream,
            params=params,
            model_id=model_id,
        )

        if stream:
            return StreamingResponse(
                cast(AsyncGenerator[str, None], generator),
                media_type="text/event-stream",
            )
        else:
            # For non-streaming, get the first (and only) item from the generator
            response_data = await generator.__anext__()
            return cast(Dict[str, Any], response_data)
