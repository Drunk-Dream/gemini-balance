from typing import Any, Dict, Union

from app.api.v1.schemas.chat import ChatCompletionRequest
from app.core.concurrency import ConcurrencyTimeoutError
from app.core.config import settings
from app.core.logging import app_logger
from app.services.base_service import ApiService
from starlette.responses import StreamingResponse
from starlette.status import HTTP_503_SERVICE_UNAVAILABLE

logger = app_logger


class OpenAIService(ApiService):
    def __init__(self):
        super().__init__(
            base_url=settings.OPENAI_API_BASE_URL, service_name="OpenAI API"
        )

    def _get_api_url(self) -> str:
        return "/v1beta/openai/chat/completions"

    def _prepare_headers(self, api_key: str) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

    def _handle_thinking_config(self, request_data: ChatCompletionRequest) -> None:
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

    async def create_chat_completion(
        self, request_data: ChatCompletionRequest
    ) -> Union[Dict[str, Any], StreamingResponse]:
        try:
            async with self.concurrency_manager.timeout_semaphore():
                url = self._get_api_url()
                stream = bool(request_data.stream)  # 确保 stream 是 bool 类型

                self._handle_thinking_config(request_data)

                params = {"alt": "sse"} if stream else {"alt": "json"}

                response = await self._send_request(
                    method="POST",
                    url=url,
                    request_data=request_data,
                    stream=stream,
                    params=params,
                    model_id=request_data.model,  # 传递 model_id
                )

                # 如果是流式响应，需要确保返回的 StreamingResponse 使用正确的 media_type
                if stream and isinstance(response, StreamingResponse):
                    response.media_type = "text/event-stream"
                return response
        except ConcurrencyTimeoutError as e:
            logger.warning(f"OpenAI API 请求并发超时: {e}")
            return StreamingResponse(
                content=f'{{"error": "{e}"}}',
                status_code=HTTP_503_SERVICE_UNAVAILABLE,
                media_type="application/json",
            )
