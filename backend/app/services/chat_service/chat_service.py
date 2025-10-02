from __future__ import annotations

import asyncio
import random
import secrets
from datetime import datetime
from typing import TYPE_CHECKING, Any, AsyncGenerator, Dict, Union, cast
from zoneinfo import ZoneInfo

import httpx
from fastapi import Depends, HTTPException
from starlette.responses import StreamingResponse
from starlette.status import (
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_503_SERVICE_UNAVAILABLE,
)

from backend.app.api.v1.schemas.chat import ChatCompletionRequest as OpenAIRequest
from backend.app.api.v1beta.schemas.gemini import Request as GeminiRequest
from backend.app.core.concurrency import (
    ConcurrencyTimeoutError,
    get_concurrency_manager,
)
from backend.app.core.config import Settings, get_settings
from backend.app.core.errors import ErrorType, StreamingCompletionError
from backend.app.core.logging import app_logger as logger
from backend.app.core.logging import transaction_logger
from backend.app.services.chat_service.types import RequestInfo
from backend.app.services.key_managers.background_tasks import (
    BackgroundTaskManager,
    get_background_task_manager,
)
from backend.app.services.key_managers.db_manager import KeyType
from backend.app.services.key_managers.key_state_manager import KeyStateManager
from backend.app.services.request_logs.request_log_manager import RequestLogManager
from backend.app.services.request_logs.schemas import RequestLog
from backend.app.services.request_service.base_request_service import BaseRequestService
from backend.app.services.request_service.gemini_request_service import (
    GeminiRequestService,
    get_gemini_request_service,
)
from backend.app.services.request_service.openai_request_service import (
    OpenAIRequestService,
    get_openai_request_service,
)

if TYPE_CHECKING:
    from backend.app.core.concurrency import ConcurrencyManager


class ChatService:
    """
    Handles chat completion logic, including API key management, retry mechanisms,
    concurrency control, and dispatching requests to specific API services.
    """

    def __init__(
        self,
        settings: Settings = Depends(get_settings),
        key_manager: KeyStateManager = Depends(KeyStateManager),
        request_log_manager: RequestLogManager = Depends(RequestLogManager),
        background_task_manager: BackgroundTaskManager = Depends(
            get_background_task_manager
        ),
        concurrency_manager: ConcurrencyManager = Depends(get_concurrency_manager),
        gemini_request_service: GeminiRequestService = Depends(
            get_gemini_request_service
        ),
        openai_request_service: OpenAIRequestService = Depends(
            get_openai_request_service
        ),
    ):
        self.settings = settings
        self._key_manager = key_manager
        self._request_log_manager = request_log_manager
        self._background_task_manager = background_task_manager
        self._concurrency_manager = concurrency_manager
        self._request_services: Dict[str, BaseRequestService] = {
            "gemini": gemini_request_service,
            "openai": openai_request_service,
        }

        self._max_retries = settings.MAX_RETRIES
        self._request_timeout_seconds = settings.REQUEST_TIMEOUT_SECONDS
        self._no_key_wait_seconds = settings.NO_KEY_WAIT_SECONDS
        self._cloudflare_gateway_enabled = settings.CLOUDFLARE_GATEWAY_ENABLED
        self._cf_ai_authorization_key = settings.CF_AI_AUTHORIZATION_KEY
        self._rate_limit_default_wait_seconds = settings.RATE_LIMIT_DEFAULT_WAIT_SECONDS
        self._key_in_use_timeout_seconds = settings.KEY_IN_USE_TIMEOUT_SECONDS

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
            key_brief=key.brief,
        )
        await self._request_log_manager.record_request_log(log_entry)

    async def _execute_request_with_retries(
        self,
        request_data: GeminiRequest | OpenAIRequest,
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
            logger.info(
                f"[Request ID: {request_id}] Attempt {attempt + 1}/{max_retries}: Using key {key.brief}."
            )

            # 启动一个定时任务，在超时后自动释放密钥
            self._background_task_manager.create_timeout_task(
                key=key,
                key_in_use_timeout_seconds=self._key_in_use_timeout_seconds,
            )

            try:
                async for chunk in self._attempt_single_request(key, request_data):
                    yield chunk
                await self._finalize_successful_request(key)
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
    ) -> AsyncGenerator[Union[str, Dict[str, Any]], None]:
        """
        Attempts a single API request, handling key preparation and dispatching to the correct request service.
        """
        # Determine which request service to use based on the request data type
        if isinstance(request_data, GeminiRequest):
            service = self._request_services["gemini"]
        elif isinstance(request_data, OpenAIRequest):
            service = self._request_services["openai"]
        else:
            raise TypeError(f"Unsupported request data type: {type(request_data)}")

        async for chunk in cast(
            AsyncGenerator[Union[str, Dict[str, Any]], None],
            service.send_request(
                key=key,
                request_data=request_data,
                request_info=self.request_info,
                cloudflare_gateway_enabled=self._cloudflare_gateway_enabled,
                cf_ai_authorization_key=self._cf_ai_authorization_key,
            ),
        ):
            yield chunk

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
                "[Request ID: %s] Error response from API with key %s: %s",
                request_id,
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
        else:
            log_level(
                f"[Request ID: {request_id}] An unexpected error occurred with key {key.brief}: {e}. Deactivating and retrying..."
            )
            # raise HTTPException(
            #     status_code=500, detail=f"An unexpected error occurred: {e}"
            # )

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
            key_brief=key.brief,
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
    ) -> Union[Dict[str, Any], StreamingResponse]:
        """
        Handles sending the HTTP request by dispatching to the appropriate generator.
        """
        generator = self._execute_request_with_retries(
            request_data=request_data,
        )

        if self.request_info.stream:
            return StreamingResponse(
                cast(AsyncGenerator[str, None], generator),
                media_type="text/event-stream",
            )
        else:
            # For non-streaming, iterate through the generator to ensure _finalize_successful_request is called
            # and collect the full response.
            response_chunks = []
            async for chunk in generator:
                response_chunks.append(chunk)
            # Assuming non-streaming requests yield a single dictionary chunk
            if response_chunks:
                return cast(Dict[str, Any], response_chunks[0])
            else:
                # Handle case where no response was yielded (e.g., due to an error handled internally)
                raise HTTPException(
                    status_code=500,
                    detail="No response data received for non-streaming request.",
                )

    async def create_chat_completion(
        self,
        request_data: GeminiRequest | OpenAIRequest,
    ):
        """
        Creates a chat completion request, handling concurrency and error responses.
        """
        request_id = self.request_info.request_id
        logger.info(
            f"[Request ID: {request_id}] Receives request from "
            f"'{self.request_info.auth_key_alias}' for model: {self.request_info.model_id}, stream: {self.request_info.stream}"
        )

        try:
            async with self._concurrency_manager.timeout_semaphore():
                return await self._dispatch_request(request_data)
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
