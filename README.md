# Gemini Balance: 为大语言模型设计的安全可观测 API 网关

本项目是一个基于 Python FastAPI 的 Google Gemini 与 OpenAI API 请求转发服务。其核心是提供一个具备**用户认证**和**双层密钥管理**的中间层，能够无缝转发符合 Google Gemini 或 OpenAI API 格式的请求，并完整支持普通和流式响应。

## 核心特性

- **统一 API 入口**: 为客户端提供统一的访问端点，无需直接处理 Google Gemini 或 OpenAI API 的复杂性。
- **分级安全与双层密钥管理**:
  - **用户级 API 密钥**: 用户可通过登录系统，安全地生成、管理和轮换自己的 API 密钥，用于访问本服务。
  - **服务级密钥池**: 集中管理用于请求上游大模型 API 的一组密钥，实现密钥轮询、冷却和状态持久化，减少客户端直接暴露密钥的风险。
- **增强的可观测性**:
  - **请求级 ID 追踪**: 为每个请求分配唯一 ID，贯穿日志系统，极大提升问题排查效率。
  - **用户密钥调用次数跟踪**: 实时追踪每个用户 API 密钥的使用情况，现在通过聚合请求日志动态计算，更准确、可审计。
  - **请求日志管理与前端筛选**: 提供详细的请求日志管理界面和筛选功能，使用户能够更好地监控和分析 API 使用情况。
  - **服务密钥池状态可视化**: 提供密钥是否“使用中”的实时状态，优化密钥调度。
- **可插拔的持久化后端**: 支持通过配置在 **异步 SQLite (`aiosqlite`)** 之间无缝切换，并具备自动化的数据库迁移系统。
- **并发管理**: 通过并发控制器 (`asyncio.Semaphore`) 对发往外部 API 的请求数进行限制，保护服务稳定，防止过载。
- **现代化的前后端架构**:
  - **后端**: 基于 FastAPI，充分利用异步特性和依赖注入。
  - **前端**: 使用 **Svelte 5 (Runes)** 构建的响应式前端界面，由后端统一托管。

## 技术栈

- **后端**: FastAPI, Pydantic, `uv`
- **前端**: SvelteKit (Svelte 5)
- **认证**: JWT, `python-jose[cryptography]`, `passlib[bcrypt]`
- **HTTP 客户端**: `httpx`
- **异步**: Python `asyncio`, `aiosqlite`
- **数据持久化**: SQLite
- **容器化**: Docker, Docker Compose

## 项目结构

```
gemini-balance/
├── backend/
│   ├── app/
│   │   ├── api/      # API 端点定义 (v1, api)
│   │   ├── core/     # 核心配置、并发与安全
│   │   └── services/ # 业务逻辑、密钥管理与聊天服务
│   └── main.py     # 应用入口
├── frontend/
│   └── src/        # Svelte 5 前端源码
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
    `bash
    docker-compose up -d --build
    `
    服务将在 `http://localhost:8090` 启动。

### 2. 本地运行 (开发环境)

1.  **构建前端**
    首先，编译前端静态文件。

    ```bash
    npm install --prefix frontend
    npm run build --prefix frontend
    ```

2.  **启动后端服务**
    ```bash
    uv sync
    uv run uvicorn backend.app.main:app --host 0.0.0.0 --port 8090 --reload
    ```
    后端服务将在 `http://localhost:8090` 启动，并托管前端界面。

## API 端点

API 分为 `api` (管理) 和 `v1`,`v1beta` (转发) 两个版本。所有管理端点都需要通过 `/api/auth/login` 获取 Bearer Token 进行认证。

### 认证 (`/api/auth`)

- **POST** `/login`
  - **描述**: 用户登录，成功后返回 JWT 访问令牌。
  - **请求体**: `application/x-www-form-urlencoded`，包含 `username` (任意) 和 `password`。

### 用户 API 密钥管理 (`/api/auth_keys`)

- **GET / POST / PUT / DELETE** `/`
  - **描述**: 对用户个人 API 密钥进行增、删、改、查操作。这些密钥用于认证对本转发服务的访问。

### 服务密钥池管理 (`/api/keys`)

- **GET / POST** `/`
  - **描述**: 添加一个或多个服务密钥到池中，或获取池中所有密钥。
- **DELETE** `/{key_identifier}`
  - **描述**: 从池中删除一个指定的服务密钥。
- **POST** `/{key_identifier}/reset`
  - **描述**: 重置指定服务密钥的状态。
- **POST** `/reset`
  - **描述**: 重置所有服务密钥的状态。

### API 代理 (`/v1`)

- **POST** `/chat/completions`
  - **描述**: 代理符合 OpenAI 格式的 `chat/completions` 请求，并根据请求内容自动转发至 Gemini 或 OpenAI。

### API 代理 (`/v1beta`)

- **POST** `/chat/completions`
  - **描述**: 代理符合 Gemini 格式的请求，并根据请求内容自动转发至 Gemini 。

### 状态与日志 (`/api`)

- **GET** `/status/keys`
  - **描述**: 返回服务密钥池中所有 API 密钥的详细状态。
- **GET** `/request-logs`
  - **描述**: 提供查询和检索详细请求日志的功能，支持多种筛选条件。
- **GET** `/logs`
  - **描述**: 获取最新的 N 条日志。
- **GET** `/logs/sse`
  - **描述**: 通过 Server-Sent Events (SSE) 实时推送最新的日志。
