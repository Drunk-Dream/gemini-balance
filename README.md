# Gemini Balance API

本项目是一个基于 Python FastAPI 的 Google Gemini API 请求转发服务。它提供了一个具备用户认证和双层密钥管理的中间层，能够无缝转发符合 Google Gemini API 格式的请求，并支持普通和流式响应。

## 功能特性

- **请求转发**: 将客户端请求安全地转发至 Google Gemini API 和 OpenAI API。
- **双层密钥管理**:
    - **用户级 API 密钥**: 允许用户登录后生成和管理自己的 API 密钥，用于访问本服务。
    - **服务级密钥池**: 集中管理用于请求 Google Gemini 的一组 API 密钥，实现密钥轮询、冷却和状态持久化。
- **用户认证**: 提供基于 JWT 的登录认证，保护管理接口。
- **可插拔的持久化**: 支持通过配置动态选择 Redis 或异步 SQLite (`aiosqlite`) 作为密钥管理的持久化后端。
- **前后端一体化**: 提供基于 Svelte 的前端界面，用于管理两类密钥和查看日志。
- **配置管理**: 通过环境变量灵活配置应用。
- **结构化日志**: 详细的日志输出，便于监控和问题排查。

## 技术栈

- **后端**: FastAPI, Pydantic, `aiosqlite`
- **前端**: SvelteKit
- **认证**: JWT, `python-jose[cryptography]`, `passlib[bcrypt]`
- **HTTP 客户端**: httpx
- **异步**: Python `asyncio`
- **容器化**: Docker, Docker Compose
- **数据持久化**: Redis, SQLite

## 项目结构

```
gemini-balance/
├── backend/
│   ├── app/
│   │   ├── api/      # API 端点定义
│   │   ├── core/     # 核心配置与安全
│   │   └── services/ # 业务逻辑与密钥管理
│   └── main.py     # 应用入口
├── frontend/
│   └── src/        # Svelte 前端源码
├── docker-compose.yml
└── README.md
```

## 安装与运行

### 1. 使用 Docker Compose (推荐)

这是最简单的启动方式，它会同时构建和运行所有服务。

1.  **克隆仓库**
    ```bash
    git clone https://github.com/Drunk-Dream/gemini-balance.git
    cd gemini-balance
    ```
2.  **配置环境变量**
    复制 `.env.example` 为 `.env`，并根据需要修改其中的配置，如 `PASSWORD` 和 `SECRET_KEY`。
    ```bash
    cp .env.example .env
    ```
3.  **启动服务**
    ```bash
    docker-compose up -d --build
    ```
服务将在 `http://localhost:8090` 启动。

### 2. 本地运行 (开发环境)

1.  **构建前端**
    首先，编译前端静态文件。
    ```bash
    cd frontend
    npm install
    npm run build
    ```
2.  **准备后端静态文件**
    将编译好的前端文件复制到后端目录。
    ```bash
    # On Windows (PowerShell)
    Copy-Item -Path frontend/build -Destination backend/frontend -Recurse -Force
    # On macOS/Linux
    cp -r frontend/build backend/frontend/
    ```
    *或者，您可以创建一个符号链接以避免每次都复制。*

3.  **启动后端服务**
    ```bash
    cd backend
    uv sync
    uv run -m main
    ```
    后端服务将在 `http://localhost:8090` 启动，并托管前端界面。

## API 端点

所有管理端点都需要通过 `/auth/login` 获取 Bearer Token 进行认证。

### 认证

- **POST** `/auth/login`
  - **描述**: 用户登录，成功后返回 JWT 访问令牌。
  - **请求体**: `application/x-www-form-urlencoded`，包含 `username` (任意) 和 `password`。

### 用户 API 密钥管理

- **GET / POST / PUT / DELETE** `/auth_keys`
  - **描述**: 对用户个人 API 密钥进行增、删、改、查操作。这些密钥用于认证对本转发服务的访问。

### 服务密钥池管理 (Gemini)

- **POST** `/keys`
  - **描述**: 向服务密钥池中添加一个或多个 Google Gemini API 密钥。
- **DELETE** `/keys/{key_identifier}`
  - **描述**: 从池中删除一个指定的 Gemini 密钥。
- **POST** `/keys/{key_identifier}/reset`
  - **描述**: 重置指定 Gemini 密钥的状态。
- **POST** `/keys/reset`
  - **描述**: 重置所有 Gemini 密钥的状态。

### API 代理

- **POST** `/v1beta/models/{model_id}:generateContent`
  - **描述**: 代理 Google Gemini `generateContent` 请求。
- **POST** `/v1beta/models/{model_id}:streamGenerateContent`
  - **描述**: 代理 Google Gemini `streamGenerateContent` 请求。
- **POST** `/v1/chat/completions`
  - **描述**: 代理符合 OpenAI 格式的 `chat/completions` 请求。

### 状态监控

- **GET** `/status/keys`
  - **描述**: 返回服务密钥池中所有 Gemini API 密钥的详细状态。
- **GET** `/status/logs`
  - **描述**: 获取最新的 N 条日志。
- **GET** `/status/logs/sse`
  - **描述**: 通过 Server-Sent Events (SSE) 推送最新的日志。
