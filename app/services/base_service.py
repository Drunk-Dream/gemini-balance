from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, Union

import httpx
from fastapi import HTTPException
from starlette.responses import StreamingResponse

from app.core.config import settings
from app.core.logging import app_logger, setup_debug_logger
from app.services.key_manager import key_manager

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
    ) -> Union[Dict[str, Any], StreamingResponse]:
        """
        Handles sending the HTTP request, including API key management and retries.
        """
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

                if stream:
                    logger.info(
                        f"Request with key {key_identifier} succeeded (streaming)."
                    )
                    # Subclasses might need to override media_type
                    return StreamingResponse(
                        # self._stream_response(response), media_type="application/json"
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
