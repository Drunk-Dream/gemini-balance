import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from starlette.responses import StreamingResponse

from app.main import app
from app.services.gemini_service import GeminiService  # 需要导入 GeminiService

# 创建 TestClient 实例
client = TestClient(app)


@pytest.fixture
def mock_gemini_service():
    """
    为 GeminiService 创建一个模拟夹具。
    """
    # 模拟 GeminiService 的 __init__ 方法，使其不执行原始的初始化逻辑
    with patch("app.services.gemini_service.GeminiService.__init__", return_value=None):
        # 创建一个 GeminiService 实例的模拟
        mock_service_instance = MagicMock(spec=GeminiService)
        mock_service_instance.api_key = "mock_api_key"
        mock_service_instance.base_url = "http://mock-api.com"
        # 将这个模拟实例注入到 FastAPI 的依赖中
        app.dependency_overrides[GeminiService] = lambda: mock_service_instance
        yield mock_service_instance
        # 清理依赖覆盖
        app.dependency_overrides = {}


@pytest.fixture
def sample_gemini_request():
    """
    提供一个示例 Gemini 请求体。
    """
    return {
        "contents": [{"parts": [{"text": "Hello, how are you?"}]}],
        "generationConfig": {
            "temperature": 0.9,
            "topP": 1.0,
            "topK": 1,
            "candidateCount": 1,
            "maxOutputTokens": 2048,
            "stopSequences": [],
        },
        "safetySettings": [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE",
            }
        ],
    }


@pytest.fixture
def sample_gemini_response():
    """
    提供一个示例 Gemini 响应体。
    """
    return {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "I'm doing great, thanks for asking!"}],
                    "role": "model",
                },
                "finishReason": "STOP",
                "safetyRatings": [],
            }
        ],
        "promptFeedback": {"safetyRatings": []},
    }


def test_health_check():
    """
    测试健康检查端点。
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_generate_content_success(
    mock_gemini_service, sample_gemini_request, sample_gemini_response
):
    """
    测试非流式 generateContent 端点成功响应。
    """
    mock_gemini_service.generate_content.return_value = sample_gemini_response

    response = client.post(
        "/v1/models/gemini-pro:generateContent", json=sample_gemini_request
    )

    assert response.status_code == 200
    assert response.json() == sample_gemini_response
    mock_gemini_service.generate_content.assert_called_once()
    args, kwargs = mock_gemini_service.generate_content.call_args
    assert args[0] == "gemini-pro"  # model_id
    assert (
        args[1].model_dump(by_alias=True, exclude_unset=True) == sample_gemini_request
    )  # request_data
    assert args[2] is False


@pytest.mark.asyncio
async def test_generate_content_stream_success(
    mock_gemini_service, sample_gemini_request
):
    """
    测试流式 generateContent 端点成功响应。
    """

    async def mock_stream_generator():
        yield json.dumps({"chunk": 1}).encode("utf-8")
        yield json.dumps({"chunk": 2}).encode("utf-8")

    mock_gemini_service.generate_content.return_value = StreamingResponse(
        mock_stream_generator(), media_type="application/json"
    )

    response = client.post(
        "/v1/models/gemini-pro:generateContent?stream=true", json=sample_gemini_request
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

    # 读取流式响应内容
    content = b""
    for chunk in response.iter_bytes():
        content += chunk

    expected_content = b'{"chunk": 1}{"chunk": 2}'
    assert content == expected_content

    mock_gemini_service.generate_content.assert_called_once()
    args, kwargs = mock_gemini_service.generate_content.call_args
    assert args[0] == "gemini-pro"
    assert (
        args[1].model_dump(by_alias=True, exclude_unset=True) == sample_gemini_request
    )
    assert args[2] is True


@pytest.mark.asyncio
async def test_generate_content_http_error(mock_gemini_service, sample_gemini_request):
    """
    测试 generateContent 端点处理外部 HTTP 错误。
    """
    from fastapi import HTTPException

    mock_gemini_service.generate_content.side_effect = HTTPException(
        status_code=401, detail="Invalid API Key"
    )

    response = client.post(
        "/v1/models/gemini-pro:generateContent", json=sample_gemini_request
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid API Key"}
    mock_gemini_service.generate_content.assert_called_once()


@pytest.mark.asyncio
async def test_generate_content_request_error(
    mock_gemini_service, sample_gemini_request
):
    """
    测试 generateContent 端点处理网络请求错误。
    """
    from fastapi import HTTPException

    mock_gemini_service.generate_content.side_effect = HTTPException(
        status_code=500, detail="Request error: Connection refused"
    )

    response = client.post(
        "/v1/models/gemini-pro:generateContent", json=sample_gemini_request
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Request error: Connection refused"}
    mock_gemini_service.generate_content.assert_called_once()


@pytest.mark.asyncio
async def test_generate_content_invalid_input(mock_gemini_service):
    """
    测试 generateContent 端点处理无效输入。
    """
    # 模拟 generate_content 方法，确保它不会被调用
    mock_gemini_service.generate_content.side_effect = Exception(
        "This should not be called for invalid input"
    )

    invalid_request = {
        "contents": [{"parts": [{"invalid_field": "This is wrong"}]}]  # 无效字段
    }
    response = client.post(
        "/v1/models/gemini-pro:generateContent", json=invalid_request
    )

    assert response.status_code == 422
    assert "detail" in response.json()
    assert any(
        "extra_forbidden" in error["type"] for error in response.json()["detail"]
    )
    # 验证 generate_content 方法没有被调用
    mock_gemini_service.generate_content.assert_not_called()
