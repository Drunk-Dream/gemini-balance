import logging
from typing import Any, AsyncGenerator, Dict, Union

import httpx
from fastapi import HTTPException
from starlette.responses import StreamingResponse

from app.api.v1.schemas.gemini import Request as GeminiRequest
from app.core.config import settings

logger = logging.getLogger(__name__)


class GeminiService:
    def __init__(self):
        self.api_key = settings.GOOGLE_API_KEY
        self.base_url = settings.GEMINI_API_BASE_URL
        self.client = httpx.AsyncClient(base_url=self.base_url)

    async def _stream_response(
        self, response: httpx.Response
    ) -> AsyncGenerator[str, None]:
        async for chunk in response.aiter_bytes():
            yield chunk.decode("utf-8")

    async def generate_content(
        self, model_id: str, request_data: GeminiRequest, stream: bool = False
    ) -> Union[Dict[str, Any], StreamingResponse]:
        url = f"/v1beta/models/{model_id}:generateContent"
        headers = {"Content-Type": "application/json", "x-goog-api-key": self.api_key}
        params = {"alt": "json"}
        if stream:
            params["stream"] = "true"

        try:
            logger.info(
                f"Forwarding request to Gemini API: {url}"
                f" with model {model_id}, stream={stream}"
            )
            response = await self.client.post(
                url,
                json=request_data.model_dump(by_alias=True, exclude_unset=True),
                headers=headers,
                params=params,
                timeout=60.0,
            )
            response.raise_for_status()

            if stream:
                return StreamingResponse(
                    self._stream_response(response), media_type="application/json"
                )
            else:
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
            )
            raise HTTPException(
                status_code=e.response.status_code, detail=e.response.text
            )
        except httpx.RequestError as e:
            logger.error(f"Request error occurred: {e}")
            raise HTTPException(status_code=500, detail=f"Request error: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise HTTPException(
                status_code=500, detail=f"An unexpected error occurred: {e}"
            )
