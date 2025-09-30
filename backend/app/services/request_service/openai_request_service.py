from __future__ import annotations

from typing import TYPE_CHECKING, Any, AsyncGenerator, Dict, Union

from fastapi import Depends, Request

from backend.app.api.v1.schemas.chat import ChatCompletionRequest as OpenAIRequest
from backend.app.core.config import Settings, get_settings
from backend.app.core.logging import app_logger as logger
from backend.app.core.logging import transaction_logger
from backend.app.services.request_service.base_request_service import BaseRequestService

if TYPE_CHECKING:
    from backend.app.services.chat_service.types import RequestInfo
    from backend.app.services.key_managers.db_manager import KeyType


def get_openai_request_service(request: Request) -> OpenAIRequestService:
    return request.app.state.openai_request_service


class OpenAIRequestService(BaseRequestService):
    def __init__(
        self,
        settings: Settings = Depends(get_settings),
    ):
        super().__init__(
            base_url=settings.OPENAI_API_BASE_URL,
            service_name="OpenAI API",
            settings=settings,
        )

    def _set_api_url(self, model_id: str, stream: bool = False) -> str:
        # OpenAI API URL doesn't depend on model_id or stream for chat completions
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
            hasattr(request_data, "include_thoughts")
            and request_data.include_thoughts is not None
            or hasattr(request_data, "thinking_budget")
            and request_data.thinking_budget is not None
        ):
            if request_data.extra_body is None:
                request_data.extra_body = {}

            google_config = request_data.extra_body.setdefault("google", {})
            thinking_config = google_config.setdefault("thinking_config", {})

            if hasattr(request_data, "include_thoughts") and request_data.include_thoughts is not None:
                thinking_config["include_thoughts"] = request_data.include_thoughts
                del request_data.include_thoughts

            if hasattr(request_data, "thinking_budget") and request_data.thinking_budget is not None:
                thinking_config["thinking_budget"] = request_data.thinking_budget
                del request_data.thinking_budget
                # reasoning_effort 字段在 GeminiService 中处理，这里删除以避免冲突
                if hasattr(request_data, "reasoning_effort"):
                    del request_data.reasoning_effort

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

    async def send_request(
        self,
        key: KeyType,
        request_data: OpenAIRequest,
        request_info: RequestInfo,
        cloudflare_gateway_enabled: bool,
        cf_ai_authorization_key: str | None,
    ) -> AsyncGenerator[Union[str, Dict[str, Any]], None]:
        """
        发送 OpenAI API 请求，处理流式和非流式响应。
        """
        request_id = request_info.request_id
        stream = request_info.stream
        model_id = (
            request_info.model_id
        )  # Added for consistency with _set_api_url signature

        logger.info(
            f"[Request ID: {request_id}] Using API key {key.brief} for OpenAI API, stream={stream}"
        )

        headers = self._prepare_headers(key.full)
        if cloudflare_gateway_enabled and cf_ai_authorization_key:
            headers["cf-aig-authorization"] = cf_ai_authorization_key

        url = self._set_api_url(model_id, stream)

        # 处理 thinking_config
        self._handle_thinking_config(request_data)

        # 检查并删除 'seed' 字段，因为 OpenAI API 不支持此字段
        if hasattr(request_data, "seed") and request_data.seed is not None:
            del request_data.seed

        if cloudflare_gateway_enabled:
            request_data.model = f"google-ai-studio/{request_data.model}"

        if stream:
            if request_data.stream_options is None:
                request_data.stream_options = {"include_usage": True}
            else:
                request_data.stream_options["include_usage"] = True

        transaction_logger.info(
            "[Request ID: %s] Request to OpenAI API with key %s: %s",
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
            ):
                yield chunk
        else:
            async for chunk in self._send_non_streaming_request(
                request_data=request_data,
                request_info=request_info,
                headers=headers,
                url=url,
            ):
                yield chunk
