# Gemini Balance API

本项目旨在开发一个基于 Python FastAPI 的 Google Gemini API 请求转发服务。其核心目标是提供一个中间层，能够接收符合 Google Gemini API 格式的请求，并将其无缝转发至 Google Gemini 官方 API，然后将接收到的响应原样返回给客户端。这包括对普通响应和流式响应的全面支持，确保转发服务具备原 API 的所有功能。

## 功能特性

- **请求转发**: 将客户端请求转发至 Google Gemini API。
- **响应返回**: 将 Gemini API 的响应原样返回给客户端，支持普通响应和流式响应。
- **API 密钥管理**: 引入 `KeyManager`，支持 API 密钥的轮询、冷却和指数退避，提高服务可靠性。
- **服务抽象**: 引入 `ApiService` 基类，抽象通用 API 交互逻辑，减少代码重复。
- **配置管理**: 通过环境变量灵活配置 API Key 和其他设置，包括 API 密钥冷却时间。
- **日志记录**: 详细的结构化日志输出，支持主应用日志、事务日志和可选的调试日志（通过 `RotatingFileHandler` 管理），便于监控和问题排查。
- **健康检查**: 提供 `/health` 端点用于服务健康状态检查。

## 技术栈

- **后端框架**: FastAPI
- **HTTP 客户端**: httpx
- **数据验证**: Pydantic
- **环境变量管理**: python-dotenv
- **Google Gemini SDK**: google-generativeai
- **异步**: Python `asyncio`
- **容器化**: Docker, Docker Compose
- **测试**: pytest, pytest-asyncio

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
│   │   ├── openai/
│   │   │   ├── endpoints/
│   │   │   │   └── chat.py
│   │   │   └── schemas/
│   │   │       └── chat.py
│   │   └── v1beta/
│   │       ├── endpoints/
│   │       │   └── gemini.py
│   │       └── schemas/
│   │           └── gemini.py
│   ├── core/
│   │   ├── config.py
│   │   └── logging.py
│   ├── services/
│   │   ├── base_service.py
│   │   ├── gemini_service.py
│   │   ├── key_manager.py
│   │   └── openai_service.py
│   └── main.py
├── pyproject.toml
├── README.md
└── tests/
    ├── test_gemini.py
    └── test_key_manager.py
```

## 安装与运行

### 1. 克隆仓库

```bash
git clone https://github.com/your-repo/gemini-balance.git
cd gemini-balance
```

### 2. 配置环境变量

创建 `.env` 文件，并根据 `.env.example` 填写您的 Google Gemini API Key。

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```
GOOGLE_API_KEY="YOUR_GEMINI_API_KEY"
```

### 3. 使用 Docker Compose 启动服务

本项目推荐使用 Docker Compose 进行部署，它会同时启动应用服务和代理服务。

```bash
docker-compose up -d
```

服务将在 `http://localhost:8000` 启动。您可以通过访问 `http://localhost:8000/docs` 查看 API 文档。

### 4. (可选) 本地运行

如果您希望在本地直接运行，请确保已安装 `uv` 并执行以下命令：

```bash
# 安装依赖
uv sync

# 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API 端点

### 健康检查

- **GET** `/health`
  - **响应**: `{"status": "ok"}`

### Gemini 内容生成

- **POST** `/v1beta/models/{model_id}:generateContent`
  - **参数**:
    - `model_id` (path): Gemini 模型 ID (例如 `gemini-pro`)
  - **请求体**: 遵循 Google Gemini API 的 `GenerateContentRequest` 格式。
  - **响应**: 遵循 Google Gemini API 的 `GenerateContentResponse` 格式，支持流式响应。
- **POST** `/v1beta/models/{model_id}:streamGenerateContent`
  - **参数**:
    - `model_id` (path): Gemini 模型 ID (例如 `gemini-pro`)
  - **请求体**: 遵循 Google Gemini API 的 `GenerateContentRequest` 格式。
  - **响应**: 流式响应。
- **POST** `/v1/chat/completions`
  - **请求体**: 遵循 OpenAI `chat.completions` API 格式。
  - **响应**: 遵循 OpenAI `chat.completions` API 格式，支持流式响应。

## 日志

日志将输出到控制台和项目根目录下的 `logs/app.log` 文件。日志级别可在 `.env` 文件中配置。

## 测试

本项目包含针对 `KeyManager` 和 `Gemini` 服务的单元测试。
- 所有自动化测试代码应统一放置于 `tests/` 目录，使用 `test_` 前缀命名，例如 `test_xxx.py`。
- 推荐使用 `pytest` 工具进行测试组织与断言，测试代码同样需加类型提示。
- 测试用例应避免对覆盖率、持续集成（CI）和测试数据纳入版本控制的硬性要求。
- 如因外部依赖数据文件缺失，需用 `pytest.mark.skipif` 跳过该测试，并给出原因说明。
- 测试代码及其断言风格，需通过 `Flake8` 检查，要求与主代码一致的代码风格和结构。
- 测试代码示例：

  ```python
  import pytest

  @pytest.mark.skipif(not Path("data/example.csv").exists(), reason="缺测试数据")
  def test_xxx():
      ...
