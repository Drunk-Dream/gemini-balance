from __future__ import annotations

import asyncio
import json
import random
import secrets
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, AsyncGenerator, Dict, Union, cast

import httpx
import httpx_sse
from fastapi import HTTPException
from pydantic import BaseModel
from starlette.responses import StreamingResponse
from starlette.status import (
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_503_SERVICE_UNAVAILABLE,
)

from backend.app.core.concurrency import ConcurrencyTimeoutError, concurrency_manager
from backend.app.core.config import settings
from backend.app.core.errors import StreamingCompletionError
from backend.app.core.logging import app_logger as logger
from backend.app.core.logging import transaction_logger

if TYPE_CHECKING:
    from backend.app.api.v1.schemas.chat import ChatCompletionRequest as OpenAIRequest
    from backend.app.api.v1beta.schemas.gemini import Request as GeminiRequest
    from backend.app.services.key_managers.key_state_manager import KeyStateManager


class RequestInfo(BaseModel):
    request_id: str
    model_id: str
    auth_key_alias: str = "anonymous"
    stream: bool
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class ApiService(ABC):
    """
    Base class for API services, handling common logic like HTTP client,
    API key api, retry mechanisms, and streaming responses.
    """

    def __init__(
        self,
        base_url: str,
        service_name: str,
        key_manager: KeyStateManager,
    ):
        self.base_url = base_url
        self.service_name = service_name
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(settings.REQUEST_TIMEOUT_SECONDS),
        )
        self.max_retries = settings.MAX_RETRIES
        self.concurrency_manager = concurrency_manager
        self._key_manager = key_manager

    def _handle_exception_response(
        self,
        e: Exception,
        status_code: int,
        error_message: str,
    ) -> Union[StreamingResponse, HTTPException]:
        """
        Handles exception responses, returning a StreamingResponse for stream requests
        or raising an HTTPException for non-stream requests.
        """
        if self.request_info.stream:
            return StreamingResponse(
                content=f'{{"error": "{error_message}: {e}"}}',
                status_code=status_code,
                media_type="application/json",
            )
        else:
            raise HTTPException(status_code=status_code, detail=f"{error_message}: {e}")

    async def _recreate_client(self):
        """
        Closes the current httpx client and creates a new one.
        This is useful for recovering from connection errors.
        """
        request_id = self.request_info.request_id
        if self.client:
            await self.client.aclose()
            logger.info(
                f"[Request ID: {request_id}] Closed existing httpx client for {self.service_name}."
            )
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(settings.REQUEST_TIMEOUT_SECONDS),
        )
        logger.info(
            f"[Request ID: {request_id}] Recreated httpx client for {self.service_name}."
        )

    @abstractmethod
    def _get_api_url(self, *args, **kwargs) -> str:
        """
        Abstract method to get the specific API endpoint URL.
        Must be implemented by subclasses.
        """
        raise NotImplementedError

    @abstractmethod
    def _prepare_headers(self, api_key: str) -> Dict[str, str]:
        """
        Abstract method to prepare request headers, including API key.
        Must be implemented by subclasses.
        """
        raise NotImplementedError

    @abstractmethod
    def _extract_and_update_token_counts(
        self, response_data: Dict[str, Any], request_info: RequestInfo
    ) -> None:
        """
        Abstract method to extract token counts from the API response and update RequestInfo.
        Must be implemented by subclasses.
        """
        raise NotImplementedError

    @abstractmethod
    def _extract_and_update_token_counts_from_stream(
        self, chunk_data: Dict[str, Any], request_info: RequestInfo
    ) -> bool:
        """
        Abstract method to extract token counts from the API response stream and update RequestInfo.
        Must be implemented by subclasses.
        """
        raise NotImplementedError

    async def _handle_stream_request_logic(
        self,
        key_identifier: str,
        method: str,
        url: str,
        request_data: GeminiRequest | OpenAIRequest,
        headers: Dict[str, str],
        params: Dict[str, str],
    ) -> AsyncGenerator[str, None]:
        """
        Handles the streaming request logic, including SSE connection, token counting,
        and error handling for streaming responses.
        """
        request_id = self.request_info.request_id
        full_response_content = ""
        async with httpx_sse.aconnect_sse(
            self.client,
            method,
            url,
            json=request_data.model_dump(by_alias=True, exclude_unset=True),
            headers=headers,
            params=params,
        ) as event_source:
            event_source.response.raise_for_status()
            stream_finished = False

            async for sse in event_source.aiter_sse():
                transaction_logger.info(
                    f"[Request ID: {request_id}] SSE event: {sse.event}, data: {sse.data}"
                )
                full_response_content += sse.data
                yield f"data: {sse.data}\n\n"

                if sse.data == "[DONE]":
                    continue

                try:
                    chunk_data = json.loads(sse.data)
                    stream_finished = self._extract_and_update_token_counts_from_stream(
                        chunk_data, self.request_info
                    )
                except json.JSONDecodeError:
                    logger.warning(
                        f"[Request ID: {request_id}] Could not decode JSON from SSE data"
                    )
                    continue

            if not stream_finished:
                logger.error(
                    f"[Request ID: {request_id}] Streaming request finished without a STOP signal. "
                )
                transaction_logger.error(
                    f"[Request ID: {request_id}] Streaming request finished without a STOP signal. "
                    f"Full response: {full_response_content}"
                )
                # Yield an error message to the client before returning
                # yield 'data: {{"error": "Streaming request finished without a STOP signal."}}\n\n'
                raise StreamingCompletionError(
                    f"Streaming request finished without a STOP signal. Full response: {full_response_content}"
                )

        await self._key_manager.mark_key_success(
            key_identifier,
            self.request_info.request_id,
            self.request_info.auth_key_alias,
            self.request_info.model_id,
            self.request_info.prompt_tokens,
            self.request_info.completion_tokens,
            self.request_info.total_tokens,
        )
        logger.info(
            f"[Request ID: {request_id}] Streaming request with key {key_identifier} succeeded. "
            f"Tokens: prompt={self.request_info.prompt_tokens}, "
            f"completion={self.request_info.completion_tokens}, "
            f"total={self.request_info.total_tokens}"
        )

    async def _handle_non_stream_request_logic(
        self,
        key_identifier: str,
        method: str,
        url: str,
        request_data: GeminiRequest | OpenAIRequest,
        headers: Dict[str, str],
        params: Dict[str, str],
    ) -> Dict[str, Any]:
        """
        Handles the non-streaming request logic, including HTTP request, token counting,
        and error handling for non-streaming responses.
        """
        request_id = self.request_info.request_id
        response = await self.client.request(
            method,
            url,
            json=request_data.model_dump(by_alias=True, exclude_unset=True),
            headers=headers,
            params=params,
        )
        response.raise_for_status()
        response_json = response.json()

        self._extract_and_update_token_counts(response_json, self.request_info)
        await self._key_manager.mark_key_success(
            key_identifier,
            self.request_info.request_id,
            self.request_info.auth_key_alias,
            self.request_info.model_id,
            self.request_info.prompt_tokens,
            self.request_info.completion_tokens,
            self.request_info.total_tokens,
        )
        transaction_logger.info(
            "[Request ID: %s] Response from %s API with key %s: %s",
            request_id,
            self.service_name,
            key_identifier,
            response_json,
        )
        logger.info(
            f"[Request ID: {request_id}] Request with key {key_identifier} succeeded. "
            f"Tokens: prompt={self.request_info.prompt_tokens}, "
            f"completion={self.request_info.completion_tokens}, "
            f"total={self.request_info.total_tokens}"
        )
        return response_json

    async def _request_generator(
        self,
        method: str,
        url: str,
        request_data: GeminiRequest | OpenAIRequest,
        params: Dict[str, str],
    ) -> AsyncGenerator[Union[str, Dict[str, Any]], None]:
        """
        A unified generator to handle both streaming and non-streaming requests.
        It manages API key rotation, retries, and error handling.
        """
        last_exception = None
        stream = self.request_info.stream
        request_id = self.request_info.request_id
        for attempt in range(self.max_retries):
            key_identifier = await self._key_manager.get_next_key(
                self.request_info.request_id, self.request_info.auth_key_alias
            )
            if not key_identifier:
                logger.warning(
                    f"[Request ID: {request_id}] Attempt {attempt + 1}/{self.max_retries}: No available API keys. "
                    f"Waiting for {settings.NO_KEY_WAIT_SECONDS} seconds."
                )
                last_exception = HTTPException(
                    status_code=503, detail="No available API keys."
                )
                await asyncio.sleep(settings.NO_KEY_WAIT_SECONDS)
                continue

            logger.info(
                f"[Request ID: {request_id}] Attempt {attempt + 1}/{self.max_retries}: Using API key "
                f"{key_identifier} for {self.service_name}, stream={stream}"
            )
            api_key = await self._key_manager.get_key_from_identifier(key_identifier)
            if not api_key:
                logger.error(
                    f"[Request ID: {request_id}] Attempt {attempt + 1}/{self.max_retries}: API key {key_identifier} not found."
                )
                last_exception = HTTPException(
                    status_code=503, detail=f"{key_identifier}'s mapper not found."
                )
                continue
            headers = self._prepare_headers(api_key)

            try:
                transaction_logger.info(
                    "[Request ID: %s] Request to %s API with key %s: %s",
                    request_id,
                    self.service_name,
                    key_identifier,
                    request_data.model_dump_json(by_alias=True, exclude_unset=True),
                )

                if stream:
                    async for chunk in self._handle_stream_request_logic(
                        key_identifier, method, url, request_data, headers, params
                    ):
                        yield chunk
                    return
                else:
                    response_data = await self._handle_non_stream_request_logic(
                        key_identifier, method, url, request_data, headers, params
                    )
                    yield response_data
                    return

            except StreamingCompletionError as e:
                last_exception = e
                logger.error(
                    f"[Request ID: {request_id}] Streaming completion error: {e}. Deactivating and retrying..."
                )
                await self._key_manager.mark_key_fail(
                    key_identifier,
                    "streaming_completion_error",
                    self.request_info.request_id,
                    self.request_info.auth_key_alias,
                )
                yield 'data: {{"error": {{"code": 500, "message": "Streaming completion error", "status": "error"}}}}\n\n'
                return
            except httpx.HTTPStatusError as e:
                # Safely get the response text for logging
                response_text = ""
                try:
                    response_text = e.response.text
                except httpx.ResponseNotRead:
                    # If the response body hasn't been read, try to read it.
                    try:
                        await e.response.aread()
                        response_text = e.response.text
                    except httpx.StreamClosed:
                        response_text = "<Streamed response body not available due to connection error>"
                except Exception:
                    # Catch any other unexpected errors during text access
                    response_text = "<Error reading response body>"

                if not response_text:
                    response_text = "<Response body not available>"
                transaction_logger.error(
                    "[Request ID: %s] Error response from %s API with key %s: %s",
                    request_id,
                    self.service_name,
                    key_identifier,
                    response_text,
                )
                last_exception = e
                error_type = "other_http_error"
                if e.response.status_code in [401, 403]:
                    error_type = "auth_error"
                elif e.response.status_code == 429:
                    error_type = "rate_limit_error"

                logger.warning(
                    f"[Request ID: {request_id}] API Key {key_identifier} failed with status {e.response.status_code}. "
                    f"Deactivating it. Attempt {attempt + 1}/{self.max_retries}."
                )
                await self._key_manager.mark_key_fail(
                    key_identifier,
                    error_type,
                    self.request_info.request_id,
                    self.request_info.auth_key_alias,
                )

                if e.response.status_code == 429:
                    wait_time = (
                        settings.RATE_LIMIT_DEFAULT_WAIT_SECONDS + random.randint(1, 9)
                    )
                    logger.warning(
                        f"[Request ID: {request_id}] Rate limit hit. Retrying after {wait_time} seconds."
                    )
                    await asyncio.sleep(wait_time)
                continue
            except httpx.RequestError as e:
                last_exception = e
                logger.error(
                    f"[Request ID: {request_id}] Request error with key {key_identifier}: {e}. Deactivating and retrying..."
                )
                await self._key_manager.mark_key_fail(
                    key_identifier,
                    "request_error",
                    self.request_info.request_id,
                    self.request_info.auth_key_alias,
                )
                await self._recreate_client()  # Recreate client on request errors
                continue
            except Exception as e:
                last_exception = e
                logger.critical(
                    f"[Request ID: {request_id}] An unexpected error occurred with key {key_identifier}: {e}. Deactivating and retrying..."
                )
                await self._key_manager.mark_key_fail(
                    key_identifier,
                    "unexpected_error",
                    self.request_info.request_id,
                    self.request_info.auth_key_alias,
                )
                # 即使标记失败，也需要抛出异常，因为这是不可恢复的错误
                raise HTTPException(
                    status_code=500, detail=f"An unexpected error occurred: {e}"
                )

        if last_exception:
            logger.critical(
                f"[Request ID: {request_id}] All API request attempts({self.max_retries} times) failed. Last error: {last_exception}"
            )
            if isinstance(last_exception, HTTPException):
                raise last_exception
            raise HTTPException(
                status_code=500,
                detail=f"All API request attempts failed. Last error: {str(last_exception)}",
            )
        raise HTTPException(
            status_code=500, detail="No API keys were available or processed."
        )

    async def _send_request(
        self,
        method: str,
        url: str,
        request_data: GeminiRequest | OpenAIRequest,
        params: Dict[str, str],
    ) -> Union[Dict[str, Any], StreamingResponse]:
        """
        Handles sending the HTTP request by dispatching to the appropriate generator.
        """
        generator = self._request_generator(
            method=method,
            url=url,
            request_data=request_data,
            params=params,
        )

        if self.request_info.stream:
            return StreamingResponse(
                cast(AsyncGenerator[str, None], generator),
                media_type="text/event-stream",
            )
        else:
            # For non-streaming, get the first (and only) item from the generator
            response_data = await generator.__anext__()
            return cast(Dict[str, Any], response_data)

    @abstractmethod
    async def _generate_content(
        self,
        request_data: GeminiRequest | OpenAIRequest,
    ) -> Union[Dict[str, Any], StreamingResponse]:
        """
        Handles the logic of generating content from the API, including error handling and retrying.
        """
        raise NotImplementedError

    async def create_chat_completion(
        self,
        request_data: GeminiRequest | OpenAIRequest,
    ):
        """
        Abstract method to create a chat completion request.
        Must be implemented by subclasses.
        """
        request_id = self.request_info.request_id
        logger.info(
            f"[Request ID: {request_id}] {self.service_name} receives request from "
            f"'{self.request_info.auth_key_alias}' for model: {self.request_info.model_id}, stream: {self.request_info.stream}"
        )

        try:
            async with self.concurrency_manager.timeout_semaphore():
                return await self._generate_content(request_data)
        except ConcurrencyTimeoutError as e:
            logger.warning(f"[Request ID: {request_id}] Concurrency timeout error: {e}")
            return self._handle_exception_response(
                e,
                HTTP_503_SERVICE_UNAVAILABLE,
                "Concurrency timeout error",
            )
        except Exception as e:
            logger.error(
                f"[Request ID: {request_id}] An unexpected error occurred: {e}"
            )
            return self._handle_exception_response(
                e,
                HTTP_500_INTERNAL_SERVER_ERROR,
                "An unexpected error occurred",
            )

    async def create_request_info(
        self, model_id: str, auth_key_alias: str, stream: bool
    ) -> None:
        self.request_info = RequestInfo(
            request_id=secrets.token_hex(4),
            model_id=model_id,
            auth_key_alias=auth_key_alias,
            stream=stream,
        )
