from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Union

from fastapi import Depends
from starlette.responses import StreamingResponse

from backend.app.api.v1.schemas.chat import ChatCompletionRequest as OpenAIRequest
from backend.app.api.v1beta.schemas.gemini import Request as GeminiRequest
from backend.app.core.config import Settings, get_settings
from backend.app.services.chat_service.base_service import ApiService
from backend.app.services.key_managers.key_state_manager import KeyStateManager

if TYPE_CHECKING:
    from backend.app.services.chat_service.types import RequestInfo


class GeminiService(ApiService):
    def __init__(
        self,
        settings: Settings = Depends(get_settings),
        key_manager: KeyStateManager = Depends(KeyStateManager),
    ):
        super().__init__(
            base_url=settings.GEMINI_API_BASE_URL,
            service_name="Gemini API",
            settings=settings,
            key_manager=key_manager,
        )

    def _set_api_url(self, model_id: str, stream: bool = False) -> None:
        action = "streamGenerateContent" if stream else "generateContent"
        self.url = f"/v1beta/models/{model_id}:{action}"

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
            self.request_info = request_info

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

    async def _prepare_and_send_request(
        self,
        request_data: GeminiRequest | OpenAIRequest,
    ) -> Union[Dict[str, Any], StreamingResponse]:
        if not isinstance(request_data, GeminiRequest):
            raise ValueError("request_data must be a GeminiRequest instance")
        stream = self.request_info.stream
        self._set_api_url(self.request_info.model_id, stream)
        params = {"alt": "sse"} if stream else None

        response = await self._dispatch_request(
            request_data=request_data,
            params=params,
        )

        # 如果是流式响应，需要确保返回的 StreamingResponse 使用正确的 media_type
        if stream and isinstance(response, StreamingResponse):
            response.media_type = "application/json"
        return response
