from __future__ import annotations

import asyncio
import json
import random
import secrets
from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING, Any, AsyncGenerator, Dict, Union, cast
from zoneinfo import ZoneInfo

import httpx
import httpx_sse
from fastapi import HTTPException
from starlette.responses import StreamingResponse
from starlette.status import (
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_503_SERVICE_UNAVAILABLE,
)

from backend.app.core.concurrency import ConcurrencyTimeoutError, concurrency_manager
from backend.app.core.config import Settings
from backend.app.core.errors import ErrorType, StreamingCompletionError
from backend.app.core.logging import app_logger as logger
from backend.app.core.logging import transaction_logger
from backend.app.services.chat_service.types import RequestInfo
from backend.app.services.key_managers.background_tasks import BackgroundTaskManager
from backend.app.services.key_managers.db_manager import KeyType
from backend.app.services.request_logs.schemas import RequestLog

if TYPE_CHECKING:
    from backend.app.api.v1.schemas.chat import ChatCompletionRequest as OpenAIRequest
    from backend.app.api.v1beta.schemas.gemini import Request as GeminiRequest
    from backend.app.services.key_managers.key_state_manager import KeyStateManager
    from backend.app.services.request_logs.request_log_manager import RequestLogManager


class ApiService(ABC):
    """
    Base class for API services, handling common logic like HTTP client,
    API key api, retry mechanisms, and streaming responses.
    """

    def __init__(
        self,
        base_url: str,
        service_name: str,
        settings: Settings,
        key_manager: KeyStateManager,
        request_log_manager: RequestLogManager,
        background_task_manager: BackgroundTaskManager,
    ):
        self.base_url = base_url
        self.service_name = service_name
        self.url: str
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(settings.REQUEST_TIMEOUT_SECONDS),
        )

        self._key_manager = key_manager
        self._request_log_manager = request_log_manager
        self._background_task_manager = background_task_manager

        self._max_retries = settings.MAX_RETRIES
        self._request_timeout_seconds = settings.REQUEST_TIMEOUT_SECONDS
        self._no_key_wait_seconds = settings.NO_KEY_WAIT_SECONDS
        self._cloudflare_gateway_enabled = settings.CLOUDFLARE_GATEWAY_ENABLED
        self._cf_ai_authorization_key = settings.CF_AI_AUTHORIZATION_KEY
        self._rate_limit_default_wait_seconds = settings.RATE_LIMIT_DEFAULT_WAIT_SECONDS
        self._key_in_use_timeout_seconds = settings.KEY_IN_USE_TIMEOUT_SECONDS

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
            timeout=httpx.Timeout(self._request_timeout_seconds),
        )
        logger.info(
            f"[Request ID: {request_id}] Recreated httpx client for {self.service_name}."
        )

    @abstractmethod
    def _set_api_url(self, *args, **kwargs) -> str:
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

    @abstractmethod
    async def _prepare_and_send_request(
        self,
        request_data: GeminiRequest | OpenAIRequest,
    ) -> Union[Dict[str, Any], StreamingResponse]:
        """
        Handles the logic of generating content from the API, including error handling and retrying.
        """
        raise NotImplementedError

    async def _process_streaming_response(
        self,
        key: KeyType,
        request_data: GeminiRequest | OpenAIRequest,
        headers: Dict[str, str],
        params: Dict[str, str] | None,
    ) -> AsyncGenerator[str, None]:
        """
        Handles the streaming request logic, including SSE connection, token counting,
        and error handling for streaming responses.
        """
        request_id = self.request_info.request_id
        full_response_content = ""
        async with httpx_sse.aconnect_sse(
            self.client,
            "POST",
            self.url,
            json=request_data.model_dump(by_alias=True, exclude_unset=True),
            headers=headers,
            params=params,
        ) as event_source:
            event_source.response.raise_for_status()
            stream_finished = False
            first_see = True

            async for sse in event_source.aiter_sse():
                if first_see:
                    logger.info(
                        f"[Request ID: {request_id}] Started streaming response."
                    )
                    first_see = False

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
                raise StreamingCompletionError(
                    "Streaming request finished without a STOP signal."
                )

        await self._finalize_successful_request(key)

    async def _process_non_streaming_response(
        self,
        key: KeyType,
        request_data: GeminiRequest | OpenAIRequest,
        headers: Dict[str, str],
        params: Dict[str, str] | None,
    ) -> Dict[str, Any]:
        """
        Handles the non-streaming request logic, including HTTP request, token counting,
        and error handling for non-streaming responses.
        """
        request_id = self.request_info.request_id
        response = await self.client.request(
            "POST",
            self.url,
            json=request_data.model_dump(by_alias=True, exclude_unset=True),
            headers=headers,
            params=params,
        )
        response.raise_for_status()
        response_json = response.json()

        self._extract_and_update_token_counts(response_json, self.request_info)
        transaction_logger.info(
            "[Request ID: %s] Response from %s API with key %s: %s",
            request_id,
            self.service_name,
            key.brief,
            response_json,
        )
        await self._finalize_successful_request(key)
        return response_json

    async def _finalize_successful_request(self, key: KeyType):
        """
        Finalizes a successful request by marking the key as success and logging token counts.
        """
        # 取消对应的超时任务
        self._background_task_manager.cancel_timeout_task(key)

        request_id = self.request_info.request_id
        await self._key_manager.mark_key_success(key)
        logger.info(
            f"[Request ID: {request_id}] Request with key {key.brief} succeeded. "
            f"Tokens: prompt={self.request_info.prompt_tokens}, "
            f"completion={self.request_info.completion_tokens}, "
            f"total={self.request_info.total_tokens}"
        )
        # 记录请求日志
        log_entry = RequestLog(
            id=None,
            request_id=request_id,
            request_time=datetime.now(ZoneInfo("UTC")),
            key_identifier=key.identifier,
            auth_key_alias=self.request_info.auth_key_alias,
            model_name=self.request_info.model_id,
            is_success=True,
            prompt_tokens=self.request_info.prompt_tokens,
            completion_tokens=self.request_info.completion_tokens,
            total_tokens=self.request_info.total_tokens,
        )
        await self._request_log_manager.record_request_log(log_entry)

    async def _execute_request_with_retries(
        self,
        request_data: GeminiRequest | OpenAIRequest,
        params: Dict[str, str] | None,
    ) -> AsyncGenerator[Union[str, Dict[str, Any]], None]:
        """
        A unified generator to handle both streaming and non-streaming requests.
        It manages API key rotation, retries, and error handling.
        """
        last_exception = None
        request_id = self.request_info.request_id
        max_retries = (
            self._max_retries
            if self._max_retries > 0
            else await self._key_manager.get_available_keys_count()
        )
        for attempt in range(max_retries):
            key = await self._key_manager.get_next_key()
            if not key:
                logger.warning(
                    f"[Request ID: {request_id}] Attempt {attempt + 1}/{max_retries}: No available API keys. "
                    f"Waiting for {self._no_key_wait_seconds} seconds."
                )
                last_exception = HTTPException(
                    status_code=503, detail="No available API keys."
                )
                await asyncio.sleep(self._no_key_wait_seconds)
                continue

            # 启动一个定时任务，在超时后自动释放密钥
            self._background_task_manager.create_timeout_task(
                key=key,
                key_in_use_timeout_seconds=self._key_in_use_timeout_seconds,
                key_manager=self._key_manager,
            )

            try:
                async for chunk in self._attempt_single_request(
                    key, request_data, params
                ):
                    yield chunk
                return
            except Exception as e:
                last_exception = e
                await self._handle_request_error(key, e)
                if isinstance(e, StreamingCompletionError):
                    yield 'data: {{"error": {{"code": 500, "message": "Streaming completion error", "status": "error"}}}}\n\n'
                    return
                if isinstance(e, HTTPException) and e.status_code == 500:
                    raise e
                continue

        if last_exception:
            logger.critical(
                f"[Request ID: {request_id}] All API request attempts({max_retries} times) failed. Last error: {last_exception}"
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

    async def _attempt_single_request(
        self,
        key: KeyType,
        request_data: GeminiRequest | OpenAIRequest,
        params: Dict[str, str] | None,
    ) -> AsyncGenerator[Union[str, Dict[str, Any]], None]:
        """
        Attempts a single API request, handling key preparation and dispatching to streaming/non-streaming processors.
        """
        request_id = self.request_info.request_id
        stream = self.request_info.stream

        logger.info(
            f"[Request ID: {request_id}] Using API key {key.brief} for {self.service_name}, stream={stream}"
        )

        headers = self._prepare_headers(key.full)
        if self._cloudflare_gateway_enabled and self._cf_ai_authorization_key:
            headers["cf-aig-authorization"] = self._cf_ai_authorization_key

        transaction_logger.info(
            "[Request ID: %s] Request to %s API with key %s: %s",
            request_id,
            self.service_name,
            key.brief,
            request_data.model_dump_json(by_alias=True, exclude_unset=True),
        )

        if stream:
            async for chunk in self._process_streaming_response(
                key, request_data, headers, params
            ):
                yield chunk
        else:
            response_data = await self._process_non_streaming_response(
                key, request_data, headers, params
            )
            yield response_data

    async def _handle_request_error(self, key: KeyType, e: Exception):
        """
        Handles various request errors, marks the key as failed, and performs necessary recovery actions.
        """
        request_id = self.request_info.request_id
        error_type = ErrorType.UNEXPECTED_ERROR
        log_level = logger.critical

        # 取消对应的超时任务
        self._background_task_manager.cancel_timeout_task(key)

        if isinstance(e, StreamingCompletionError):
            error_type = ErrorType.STREAMING_COMPLETION_ERROR
            log_level = logger.error
            log_level(
                f"[Request ID: {request_id}] Streaming completion error: {e}. Deactivating and retrying..."
            )
        elif isinstance(e, httpx.HTTPStatusError):
            response_text = ""
            try:
                response_text = e.response.text
            except httpx.ResponseNotRead:
                try:
                    await e.response.aread()
                    response_text = e.response.text
                except httpx.StreamClosed:
                    response_text = (
                        "<Streamed response body not available due to connection error>"
                    )
            except Exception:
                response_text = "<Error reading response body>"

            if not response_text:
                response_text = "<Response body not available>"
            transaction_logger.error(
                "[Request ID: %s] Error response from %s API with key %s: %s",
                request_id,
                self.service_name,
                key.identifier,
                response_text,
            )
            error_type = ErrorType.OTHER_HTTP_ERROR
            if e.response.status_code in [401, 403]:
                error_type = ErrorType.AUTH_ERROR
            elif e.response.status_code == 429:
                error_type = ErrorType.RATE_LIMIT_ERROR

            log_level = logger.warning
            log_level(
                f"[Request ID: {request_id}] API Key {key.brief} failed with status {e.response.status_code}. "
                f"Deactivating it."
            )

            if e.response.status_code == 429:
                wait_time = self._rate_limit_default_wait_seconds + random.randint(1, 5)
                logger.warning(
                    f"[Request ID: {request_id}] Rate limit hit. Retrying after {wait_time} seconds."
                )
                await asyncio.sleep(wait_time)
        elif isinstance(e, httpx.RequestError):
            error_type = ErrorType.REQUEST_ERROR
            log_level = logger.error
            log_level(
                f"[Request ID: {request_id}] Request error with key {key.brief}: {e}. Deactivating and retrying..."
            )
            await self._recreate_client()
        else:
            log_level(
                f"[Request ID: {request_id}] An unexpected error occurred with key {key.brief}: {e}. Deactivating and retrying..."
            )
            raise HTTPException(
                status_code=500, detail=f"An unexpected error occurred: {e}"
            )

        should_cool_down = await self._key_manager.mark_key_fail(key, error_type)
        if should_cool_down:
            self._background_task_manager.wakeup_event.set()

        log_entry = RequestLog(
            id=None,
            request_id=request_id,
            request_time=datetime.now(ZoneInfo("UTC")),
            key_identifier=key.identifier,
            auth_key_alias=self.request_info.auth_key_alias,
            model_name=self.request_info.model_id,
            is_success=False,
            error_type=error_type.value,
        )
        await self._request_log_manager.record_request_log(log_entry)

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

    async def _dispatch_request(
        self,
        request_data: GeminiRequest | OpenAIRequest,
        params: Dict[str, str] | None = None,
    ) -> Union[Dict[str, Any], StreamingResponse]:
        """
        Handles sending the HTTP request by dispatching to the appropriate generator.
        """
        generator = self._execute_request_with_retries(
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
            async with concurrency_manager.timeout_semaphore():
                return await self._prepare_and_send_request(request_data)
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
