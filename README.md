# Gemini Balance: 为大语言模型设计的安全可观测 API 网关

Gemini Balance 是一个基于 FastAPI 的转发网关，统一代理符合 Google Gemini 与 OpenAI 规范的请求，提供用户认证、双层密钥管理、请求日志与统计、前端可视化等能力。后端默认托管编译后的 SvelteKit 前端，便于一体化部署。

## 核心特性
- 统一入口：兼容 OpenAI `/v1/chat/completions` 与 Gemini `/v1beta/models/...`，支持普通与流式响应
- 双层密钥管理：用户级 API 密钥 CRUD + 服务密钥池（SQLite 持久化、冷却/超时处理、健康检查、背景任务恢复）
- 认证与安全：基于 JWT 的登录与依赖注入校验，请求级唯一 ID 贯穿日志
- 可观测性：请求日志查询与筛选、SSE 实时日志、模型/Token/成功率/热力图等统计接口
- 并发与韧性：可配置的并发控制、请求/并发超时、httpx 客户端自动重建、启动时自动迁移
- 前端体验：Svelte 5 Runes + Tailwind CSS 4，登录后自动跳转，统一的密钥管理表单，LogViewer，日期范围选择（基于实际日志数据限制），灰色调 UI 主题

## 系统架构概览
- 后端 (FastAPI)
  - 路由：`/api/auth`、`/api/auth_keys`、`/api/keys`、`/api/request_logs`、`/api/realtime_logs`、`/v1` (OpenAI Chat) 、`/v1beta` (Gemini)
  - 服务：`GeminiRequestService`、`OpenAIRequestService`（继承通用基类）、`RequestLogManager`、`ConcurrencyManager`
  - 密钥池：`KeyStateManager` + `SQLiteDBManager`，含冷却、指数退避、卡死密钥超时与健康检查；`BackgroundTaskManager` 负责状态维护
  - 数据与迁移：异步 `aiosqlite`，基于 `BaseMigrationManager` 的版本化迁移系统
  - 前端托管：检测到 `frontend/build` 后托管静态资源，否则返回后台运行提示
- 前端 (SvelteKit)
  - 路由：`/login`、`/auth-keys`、`/request-keys`、`/request-logs`、`/realtime-logs`、`/stats` 等
  - 组件：密钥管理表单、日志过滤/展示组件、通知与主题控制、基于实际数据限制的日期范围选择器、统一输入框
  - 技术：Svelte 5 Runes、Tailwind CSS 4、bits-ui、tailwind-variants、@internationalized/date、echarts（图表）、Vite 构建

## 技术栈
- 后端：Python 3.12+、FastAPI、Pydantic & pydantic-settings、httpx/httpx-sse、aiosqlite、python-jose[cryptography]、passlib[bcrypt]、Uvicorn、uv
- 前端：SvelteKit (Svelte 5 Runes)、Vite、Tailwind CSS 4、bits-ui、tailwind-variants、@internationalized/date、echarts、lucide 图标
- 其他：Docker、Docker Compose

## 项目结构
```
gemini-balance/
├── backend/
│   ├── app/
│   │   ├── api/                  # /api, /v1, /v1beta 路由
│   │   ├── core/                 # 配置、并发与日志
│   │   ├── services/             # 请求服务、密钥池、日志管理
│   │   └── main.py               # FastAPI 应用构建
│   ├── main.py                   # 读取 env，启动 uvicorn
│   └── tests/                    # HTTP 场景用例
├── frontend/
│   ├── src/routes/               # Svelte 页面（登录、密钥管理、日志、统计等）
│   └── build/                    # 生产构建产物（由后端托管）
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

## 快速开始
### 1) 使用 Docker Compose（推荐）
```bash
git clone https://github.com/Drunk-Dream/gemini-balance.git
cd gemini-balance
cp .env.example .env  # 根据需要调整 SECRET_KEY、PASSWORD、API 基础配置等
docker-compose up -d --build
```
服务默认运行在 `http://localhost:8090`，并托管前端界面。

### 2) 本地开发运行
前端构建（或开发模式）：
```bash
npm install --prefix frontend
npm run build --prefix frontend  # 或 npm run dev --prefix frontend -- --open
```
后端依赖与运行（使用 uv）：
```bash
uv sync
uv run uvicorn backend.app.main:app --host 0.0.0.0 --port 8090 --reload
```
后台启动时会自动执行数据库迁移，并服务前端静态文件（若存在 `frontend/build`）。

## API 速查
- 认证：`POST /api/auth/login` 返回 JWT
- 用户 API 密钥：`GET/POST/PUT/DELETE /api/auth_keys`
- 服务密钥池：`GET/POST /api/keys`，`DELETE /api/keys/{key_identifier}`，`POST /api/keys/{key_identifier}/reset`，`POST /api/keys/reset`
- 请求日志：`GET /api/request_logs`（查询筛选），`GET /api/logs/sse`（SSE 实时日志）
- 统计：`GET /api/stats/{endpoint}` 提供模型/Token/成功率/热力图等图表数据
- 代理：`POST /v1/chat/completions`（OpenAI 兼容），`POST /v1beta/models/{model_id}:generateContent|streamGenerateContent`（Gemini）
- 健康检查：`GET /health`

## 开发约定
- 依赖管理：统一使用 `uv` (`uv add/remove`, `uv run`)，勿直接修改 `pyproject.toml`
- 路径：使用 `pathlib` 处理文件路径，不混用 `os.path`
- 代码风格：遵循 PEP8，全部变量/函数均写类型提示，优先卫语句减少嵌套，移除未使用的 import
- 异常处理：精确捕获异常并记录日志，避免裸 `except`
- 脚本入口：定义 `main()` 并通过 `if __name__ == "__main__": raise SystemExit(main())` 调用
- 文档：函数/类/模块需提供结构化 docstring（Google/Numpy 风格），与类型提示保持一致

