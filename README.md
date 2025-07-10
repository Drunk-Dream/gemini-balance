# Gemini Balance API

本项目旨在开发一个基于 Python FastAPI 的 Google Gemini API 请求转发服务。其核心目标是提供一个中间层，能够接收符合 Google Gemini API 格式的请求，并将其无缝转发至 Google Gemini 官方 API，然后将接收到的响应原样返回给客户端。这包括对普通响应和流式响应的全面支持，确保转发服务具备原 API 的所有功能。

## 功能特性

*   **请求转发**: 将客户端请求转发至 Google Gemini API。
*   **响应返回**: 将 Gemini API 的响应原样返回给客户端，支持普通响应和流式响应。
*   **配置管理**: 通过环境变量灵活配置 API Key 和其他设置。
*   **日志记录**: 详细的日志输出，便于监控和问题排查。
*   **健康检查**: 提供 `/health` 端点用于服务健康状态检查。

## 技术栈

*   **后端框架**: FastAPI
*   **HTTP 客户端**: httpx
*   **数据验证**: Pydantic
*   **环境变量管理**: python-dotenv
*   **Google Gemini SDK**: google-generativeai
*   **异步**: Python `asyncio`

## 项目结构

```
gemini-balance/
├── .clinerules/
│   ├── coding-standards.md
│   ├── flake8-lint-waiver.md
│   └── memory/
│       └── project_info.md
├── .gitignore
├── .python-version
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   └── gemini.py
│   │       └── schemas/
│   │           └── gemini.py
│   ├── core/
│   │   ├── config.py
│   │   └── logging.py
│   ├── services/
│   │   └── gemini_service.py
│   └── main.py
├── pyproject.toml
├── README.md
└── tests/
    └── test_gemini.py
```

## 安装与运行

### 1. 克隆仓库

```bash
git clone https://github.com/your-repo/gemini-balance.git
cd gemini-balance
```

### 2. 安装依赖

本项目使用 `uv` 进行依赖管理。请确保您已安装 `uv`。

```bash
uv sync
```

### 3. 配置环境变量

创建 `.env` 文件，并根据 `.env.example` 填写您的 Google Gemini API Key。

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```
GOOGLE_API_KEY="YOUR_GEMINI_API_KEY"
```

### 4. 运行服务

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

服务将在 `http://localhost:8000` 启动。您可以通过访问 `http://localhost:8000/docs` 查看 API 文档。

## API 端点

### 健康检查

*   **GET** `/health`
    *   **响应**: `{"status": "ok"}`

### Gemini 内容生成

*   **POST** `/v1/models/{model_id}:generateContent`
    *   **参数**:
        *   `model_id` (path): Gemini 模型 ID (例如 `gemini-pro`)
        *   `stream` (query, optional): 是否启用流式响应 (默认为 `false`)
    *   **请求体**: 遵循 Google Gemini API 的 `GenerateContentRequest` 格式。
    *   **响应**: 遵循 Google Gemini API 的 `GenerateContentResponse` 格式，如果 `stream=true`，则为流式响应。

## 日志

日志将输出到控制台和项目根目录下的 `logs/app.log` 文件。日志级别可在 `.env` 文件中配置。

## 测试

暂无测试用例。
