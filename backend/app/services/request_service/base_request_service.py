from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, AsyncGenerator, Dict, Union

import httpx
import httpx_sse

from backend.app.core.errors import StreamingCompletionError
from backend.app.core.logging import app_logger as logger
from backend.app.core.logging import transaction_logger

if TYPE_CHECKING:
    from backend.app.api.v1.schemas.chat import ChatCompletionRequest as OpenAIRequest
    from backend.app.api.v1beta.schemas.gemini import Request as GeminiRequest
    from backend.app.core.config import Settings
    from backend.app.services.chat_service.types import RequestInfo
    from backend.app.services.request_key_manager.db_manager import KeyType


class BaseRequestService(ABC):
    """
    Base class for request services
    """

    def __init__(self, settings: Settings, base_url: str, service_name: str):
        self.base_url = base_url
        self.service_name = service_name
        self.settings = settings
        self.client = httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(settings.REQUEST_TIMEOUT_SECONDS),
        )

    @abstractmethod
    def _set_api_url(self, model_id: str, stream: bool = False) -> str:
        """
        Abstract method to set the API URL based on model_id and stream status.
        """
        raise NotImplementedError

    @abstractmethod
    def _prepare_headers(self, api_key: str) -> Dict[str, str]:
        """
        Abstract method to prepare request headers, including authorization.
        """
        raise NotImplementedError

    @abstractmethod
    def _extract_and_update_token_counts(
        self, response_data: Dict[str, Any], request_info: RequestInfo
    ) -> None:
        """
        Abstract method to extract token counts from a non-streaming API response and update RequestInfo.
        """
        raise NotImplementedError

    @abstractmethod
    def _extract_and_update_token_counts_from_stream(
        self, chunk_data: Dict[str, Any], request_info: RequestInfo
    ) -> bool:
        """
        Abstract method to extract token counts from a streaming API response chunk and update RequestInfo.
        Returns True if the stream has finished (e.g., STOP signal received).
        """
        raise NotImplementedError

    async def _send_streaming_request(
        self,
        request_data: GeminiRequest | OpenAIRequest,
        request_info: RequestInfo,
        headers: Dict[str, str],
        url: str,
        params: Dict[str, Any] | None = None,
    ) -> AsyncGenerator[Union[str, Dict[str, Any]], None]:
        """
        Handles the common logic for sending streaming API requests.
        """
        request_id = request_info.request_id
        full_response_content = ""
        async with httpx_sse.aconnect_sse(
            self.client,
            "POST",
            url,
            json=request_data.model_dump(by_alias=True, exclude_unset=True),
            headers=headers,
            params=params,
        ) as event_source:
            event_source.response.raise_for_status()
            stream_finished = False
            first_sse = True

            async for sse in event_source.aiter_sse():
                if first_sse:
                    logger.info(
                        f"[Request ID: {request_id}] Started streaming response."
                    )
                    first_sse = False

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
                        chunk_data, request_info
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

    async def _send_non_streaming_request(
        self,
        request_data: GeminiRequest | OpenAIRequest,
        request_info: RequestInfo,
        headers: Dict[str, str],
        url: str,
        params: Dict[str, Any] | None = None,
    ) -> AsyncGenerator[Union[str, Dict[str, Any]], None]:
        """
        Handles the common logic for sending non-streaming API requests.
        """
        request_id = request_info.request_id
        response = await self.client.request(
            "POST",
            url,
            json=request_data.model_dump(by_alias=True, exclude_unset=True),
            headers=headers,
            params=params,
        )
        response.raise_for_status()
        response_json = response.json()

        self._extract_and_update_token_counts(response_json, request_info)
        transaction_logger.info(
            "[Request ID: %s] Response from %s: %s",
            request_id,
            self.service_name,
            response_json,
        )
        yield response_json

    async def aclose(self) -> None:
        """
        Closes the httpx client.
        """
        await self.client.aclose()
        logger.info(f"Closed httpx client for {self.service_name}.")

    @abstractmethod
    async def send_request(
        self,
        key: KeyType,
        request_data: GeminiRequest | OpenAIRequest,
        request_info: RequestInfo,
        cloudflare_gateway_enabled: bool,
        cf_ai_authorization_key: str | None,
    ) -> AsyncGenerator[Union[str, Dict[str, Any]], None]:
        """
        Abstract method to send an API request, handling both streaming and non-streaming responses.
        Must be implemented by subclasses.
        """
        raise NotImplementedError
