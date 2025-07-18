from typing import Any, Dict, Union

from app.api.openai.schemas.chat import ChatCompletionRequest
from app.core.config import settings
from app.core.logging import app_logger
from app.services.base_service import ApiService
from starlette.responses import StreamingResponse

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

    async def create_chat_completion(
        self, request_data: ChatCompletionRequest
    ) -> Union[Dict[str, Any], StreamingResponse]:
        url = self._get_api_url()
        stream = bool(request_data.stream)  # 确保 stream 是 bool 类型
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
