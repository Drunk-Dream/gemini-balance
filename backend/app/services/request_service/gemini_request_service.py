from __future__ import annotations

from typing import TYPE_CHECKING, Any, AsyncGenerator, Dict, Union

from fastapi import Depends, Request

from backend.app.api.v1beta.schemas.gemini import Request as GeminiRequest
from backend.app.core.config import Settings, get_settings
from backend.app.core.logging import app_logger as logger
from backend.app.core.logging import transaction_logger
from backend.app.services.request_service.base_request_service import BaseRequestService

if TYPE_CHECKING:
    from backend.app.services.chat_service.types import RequestInfo
    from backend.app.services.key_managers.db_manager import KeyType


def get_gemini_request_service(request: Request) -> GeminiRequestService:
    return request.app.state.gemini_request_service


class GeminiRequestService(BaseRequestService):
    def __init__(
        self,
        settings: Settings = Depends(get_settings),
    ):
        super().__init__(
            base_url=settings.GEMINI_API_BASE_URL,
            service_name="Gemini API",
            settings=settings,
        )

    def _set_api_url(self, model_id: str, stream: bool = False) -> str:
        action = "streamGenerateContent" if stream else "generateContent"
        return f"/v1beta/models/{model_id}:{action}"

    def _prepare_headers(self, api_key: str) -> Dict[str, str]:
        return {"Content-Type": "application/json", "x-goog-api-key": api_key}

    def _extract_and_update_token_counts(
        self, response_data: Dict[str, Any], request_info: RequestInfo
    ) -> None:
        """
        从 Gemini API 响应中提取 token 计数并更新 RequestInfo。
        """
        usage_metadata = response_data.get("usageMetadata")
        if usage_metadata:
            request_info.prompt_tokens = usage_metadata.get("promptTokenCount")
            request_info.completion_tokens = usage_metadata.get("candidatesTokenCount")
            request_info.total_tokens = usage_metadata.get("totalTokenCount")

    def _extract_and_update_token_counts_from_stream(
        self, chunk_data: Dict[str, Any], request_info: RequestInfo
    ) -> bool:
        """
        从 Gemini API 流式响应中提取 token 计数并更新 RequestInfo。
        """
        if any(
            candidate.get("finishReason") == "STOP"
            for candidate in chunk_data.get("candidates", [])
        ):
            self._extract_and_update_token_counts(chunk_data, request_info)
            return True
        return False

    async def send_request(
        self,
        key: KeyType,
        request_data: GeminiRequest,
        request_info: RequestInfo,
        cloudflare_gateway_enabled: bool,
        cf_ai_authorization_key: str | None,
    ) -> AsyncGenerator[Union[str, Dict[str, Any]], None]:
        """
        发送 Gemini API 请求，处理流式和非流式响应。
        """
        request_id = request_info.request_id
        stream = request_info.stream
        model_id = request_info.model_id

        logger.info(
            f"[Request ID: {request_id}] Using API key {key.brief} for Gemini API, stream={stream}"
        )

        headers = self._prepare_headers(key.full)
        if cloudflare_gateway_enabled and cf_ai_authorization_key:
            headers["cf-aig-authorization"] = cf_ai_authorization_key

        url = self._set_api_url(model_id, stream)
        params = {"alt": "sse"} if stream else None

        transaction_logger.info(
            "[Request ID: %s] Request to Gemini API with key %s: %s",
            request_id,
            key.brief,
            request_data.model_dump_json(by_alias=True, exclude_unset=True),
        )

        if stream:
            async for chunk in self._send_streaming_request(
                request_data=request_data,
                request_info=request_info,
                headers=headers,
                url=url,
                params=params,
            ):
                yield chunk
        else:
            async for chunk in self._send_non_streaming_request(
                request_data=request_data,
                request_info=request_info,
                headers=headers,
                url=url,
                params=params,
            ):
                yield chunk
