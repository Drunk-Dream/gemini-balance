from typing import Any, Dict, Union

from starlette.responses import StreamingResponse

from backend.app.api.v1.schemas.chat import ChatCompletionRequest
from backend.app.api.v1beta.schemas.gemini import Request as GeminiRequest
from backend.app.core.config import settings
from backend.app.services.base_service import ApiService


class GeminiService(ApiService):
    def __init__(self):
        super().__init__(
            base_url=settings.GEMINI_API_BASE_URL, service_name="Gemini API"
        )

    def _get_api_url(self, model_id: str, stream: bool = False) -> str:
        action = "streamGenerateContent" if stream else "generateContent"
        return f"/v1beta/models/{model_id}:{action}"

    def _prepare_headers(self, api_key: str) -> Dict[str, str]:
        return {"Content-Type": "application/json", "x-goog-api-key": api_key}

    async def _generate_content(
        self,
        request_data: GeminiRequest | ChatCompletionRequest,
    ) -> Union[Dict[str, Any], StreamingResponse]:
        if not isinstance(request_data, GeminiRequest):
            raise ValueError("request_data must be a GeminiRequest instance")
        stream = self.request_info.stream
        url = self._get_api_url(self.request_info.model_id, stream)
        params = {"alt": "sse"} if stream else {"alt": "json"}

        response = await self._send_request(
            method="POST",
            url=url,
            request_data=request_data,
            params=params,
        )

        # 如果是流式响应，需要确保返回的 StreamingResponse 使用正确的 media_type
        if stream and isinstance(response, StreamingResponse):
            response.media_type = "application/json"
        return response
