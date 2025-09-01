from typing import Any, Dict, Union

from starlette.responses import StreamingResponse
from starlette.status import HTTP_503_SERVICE_UNAVAILABLE

from backend.app.api.v1beta.schemas.gemini import Request as GeminiRequest
from backend.app.core.concurrency import ConcurrencyTimeoutError
from backend.app.core.config import settings
from backend.app.core.logging import app_logger
from backend.app.services.base_service import ApiService

logger = app_logger


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

    async def generate_content(
        self, model_id: str, request_data: GeminiRequest, stream: bool = False
    ) -> Union[Dict[str, Any], StreamingResponse]:
        try:
            async with self.concurrency_manager.timeout_semaphore():
                url = self._get_api_url(model_id, stream)
                params = {"alt": "sse"} if stream else {"alt": "json"}

                response = await self._send_request(
                    method="POST",
                    url=url,
                    request_data=request_data,
                    stream=stream,
                    params=params,
                    model_id=model_id,  # 传递 model_id
                )

                # 如果是流式响应，需要确保返回的 StreamingResponse 使用正确的 media_type
                if stream and isinstance(response, StreamingResponse):
                    response.media_type = "application/json"
                return response
        except ConcurrencyTimeoutError as e:
            logger.warning(f"Gemini API 请求并发超时: {e}")
            return StreamingResponse(
                content=f'{{"error": "{e}"}}',
                status_code=HTTP_503_SERVICE_UNAVAILABLE,
                media_type="application/json",
            )
