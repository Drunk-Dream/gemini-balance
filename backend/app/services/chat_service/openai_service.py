from typing import Any, Dict, Union

from fastapi import Depends
from starlette.responses import StreamingResponse

from backend.app.api.v1.schemas.chat import ChatCompletionRequest as OpenAIRequest
from backend.app.api.v1beta.schemas.gemini import Request as GeminiRequest
from backend.app.core.config import Settings, get_settings, settings
from backend.app.services.chat_service.base_service import ApiService, RequestInfo
from backend.app.services.key_managers.key_state_manager import KeyStateManager


class OpenAIService(ApiService):
    def __init__(
        self,
        settings: Settings = Depends(get_settings),
        key_manager: KeyStateManager = Depends(KeyStateManager),
    ):
        super().__init__(
            base_url=settings.OPENAI_API_BASE_URL,
            service_name="OpenAI API",
            key_manager=key_manager,
        )

    def _get_api_url(self) -> str:
        return "/chat/completions"

    def _prepare_headers(self, api_key: str) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

    def _handle_thinking_config(self, request_data: OpenAIRequest) -> None:
        """
        处理 include_thoughts 和 thinking_budget 字段，将其转换为 extra_body 中的 google.thinking_config 结构。
        """
        if (
            request_data.include_thoughts is not None
            or request_data.thinking_budget is not None
        ):
            if request_data.extra_body is None:
                request_data.extra_body = {}

            google_config = request_data.extra_body.setdefault("google", {})
            thinking_config = google_config.setdefault("thinking_config", {})

            if request_data.include_thoughts is not None:
                thinking_config["include_thoughts"] = request_data.include_thoughts
                del request_data.include_thoughts

            if request_data.thinking_budget is not None:
                thinking_config["thinking_budget"] = request_data.thinking_budget
                del request_data.thinking_budget
                # reasoning_effort 字段在 GeminiService 中处理，这里删除以避免冲突
                if hasattr(request_data, "reasoning_effort"):
                    del request_data.reasoning_effort

    async def _generate_content(
        self,
        request_data: GeminiRequest | OpenAIRequest,
    ) -> Union[Dict[str, Any], StreamingResponse]:
        if not isinstance(request_data, OpenAIRequest):
            raise ValueError("request_data must be a ChatCompletionRequest instance")
        url = self._get_api_url()
        stream = self.request_info.stream

        self._handle_thinking_config(request_data)

        # 检查并删除 'seed' 字段，因为 OpenAI API 不支持此字段
        if hasattr(request_data, "seed") and request_data.seed is not None:
            del request_data.seed

        if settings.CLOUDFLARE_GATEWAY_ENABLED:
            request_data.model = f"google-ai-studio/{request_data.model}"

        if stream:
            if request_data.stream_options is None:
                request_data.stream_options = {"include_usage": True}
            else:
                request_data.stream_options["include_usage"] = True

        params = {"alt": "sse"} if stream else {"alt": "json"}

        response = await self._send_request(
            method="POST",
            url=url,
            request_data=request_data,
            params=params,
        )

        # 如果是流式响应，需要确保返回的 StreamingResponse 使用正确的 media_type
        if stream and isinstance(response, StreamingResponse):
            response.media_type = "text/event-stream"
        return response

    def _extract_and_update_token_counts(
        self, response_data: Dict[str, Any], request_info: RequestInfo
    ) -> None:
        """
        从 OpenAI API 响应中提取 token 计数并更新 RequestInfo。
        """
        usage = response_data.get("usage")
        if usage:
            request_info.prompt_tokens = usage.get("prompt_tokens")
            request_info.completion_tokens = usage.get("completion_tokens")
            request_info.total_tokens = usage.get("total_tokens")
            self.request_info = request_info

    def _extract_and_update_token_counts_from_stream(
        self, chunk_data: Dict[str, Any], request_info: RequestInfo
    ) -> bool:
        """
        从 OpenAI API 流式响应中提取 token 计数并更新 RequestInfo。
        """
        if any(
            choice.get("finish_reason") == "stop"
            for choice in chunk_data.get("choices", [])
        ):
            self._extract_and_update_token_counts(chunk_data, request_info)
            return True
        return False
