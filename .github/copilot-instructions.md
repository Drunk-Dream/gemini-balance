# Gemini Balance AI 代理指南

本文档为 AI 编码代理提供了在 `gemini-balance` 代码库中高效工作的核心指南。

## 关于此项目

`gemini-balance` 是一个基于 Python FastAPI 的 API 网关，专为 Google Gemini 和 OpenAI 大语言模型设计。它提供了一个具备**用户认证**、**双层密钥管理**和**可观测性**的安全中间层，能够无缝转发普通和流式请求。前端采用 Svelte 5 (Runes) 构建，并由后端统一托管。

- **后端**: FastAPI, Pydantic, httpx (Python)
- **前端**: Svelte 5 (Runes), DaisyUI 5, Tailwind CSS
- **数据库**: aiosqlite (异步 SQLite)
- **依赖管理**: `uv` (Python), `npm` (Frontend)
- **认证**: JWT (`python-jose`, `passlib`)

## 核心概念

- **双层密钥管理**:
    - **用户级 API 密钥**: 用户通过 Web UI 生成和管理，用于访问本服务。
    - **服务级密钥池**: 在后端集中管理，用于轮询和访问上游 LLM API，对前端用户透明。
- **KeyStateManager**: 位于 `backend/app/services/request_key_manager/`，是服务密钥池的核心逻辑，负责密钥的获取、归还、冷却和指数退避。
- **数据库迁移**: 系统在启动时会自动检查并应用 `backend/app/db/migrations/` 中的 SQL 脚本，实现版本化 schema 管理。
- **并发控制**: 通过 `ConcurrencyManager` (基于 `asyncio.Semaphore`) 限制对外部 API 的并发请求数。
- **请求级上下文**: 使用 `RequestInfo` 对象封装每个请求的元数据，简化服务间的参数传递。

## 关键目录结构

```
gemini-balance/
├── backend/
│   ├── app/
│   │   ├── api/      # API 端点定义 (v1, api)
│   │   ├── core/     # 核心配置、并发与安全
│   │   ├── db/       # 数据库迁移与管理
│   │   └── services/ # 业务逻辑、密钥管理与聊天服务
│   └── main.py     # 应用入口
├── frontend/
│   └── src/        # Svelte 5 前端源码
├── data/
│   └── sqlite.db   # SQLite 数据库文件
└── tests/          # Pytest 测试
```

## 开发工作流程

### 运行项目 (Docker - 推荐)

1.  复制 `.env.example` 为 `.env` 并按需修改。
2.  执行 `docker-compose up -d --build`。服务将在 `http://localhost:8090` 启动。

### 本地开发

1.  **构建前端**: `npm install --prefix frontend && npm run build --prefix frontend`
2.  **启动后端**: `uv sync && uv run uvicorn backend.app.main:app --host 0.0.0.0 --port 8090 --reload`

### 测试

- 测试使用 `pytest` 框架，所有测试文件位于 `tests/` 目录下。
- 如果测试因缺少数据文件而失败，请使用 `@pytest.mark.skipif` 跳过该测试，而不是移除它。

## 后端约定 (Python/FastAPI)

- **强制类型提示**: 所有函数和方法都必须有明确的类型提示。
- **路径操作**: 优先使用 `pathlib` 模块处理文件路径，避免使用 `os.path`。
- **依赖管理**: 始终使用 `uv add <package>` 或 `uv remove <package>` 来管理 Python 依赖，不要手动编辑 `pyproject.toml`。
- **Linter (Flake8)**:
    - 必须修复功能性错误（如未定义变量、语法错误）。
    - 可忽略纯风格警告，如 `E501` (行太长) 和 `E302` (空行不足)。
    - **例外**: 对于字符串和注释，如果出现 `E501` 警告，必须通过断行来解决。

## 前端约定 (Svelte/DaisyUI)

- **UI 库**: 项目使用 DaisyUI 5 和 Tailwind CSS，图标使用phosphor-svelte库。
- **响应式**: 前端开发基于 Svelte 5 的 Runes 实现细粒度响应式。
- **组件**: 遵循 `.github/instructions/daisyui.instructions.md` 中定义的组件用法和类名规则。这是进行任何前端开发时的重要参考。
- **颜色**: 优先使用 DaisyUI 的语义化颜色名称 (如 `primary`, `base-100`)，以确保主题切换时颜色正确。

## 配置管理

- **同步**: 当在 `backend/app/core/config.py` 中添加新的配置项时，必须在 `.env.example` 文件中同步添加对应的环境变量，并附上中文注释。
- **示例**:
  ```
  # .env.example
  # 是否启用新功能。设置为 "true" 启用，"false" 禁用。
  # 默认值：False
  NEW_FEATURE_ENABLED=False
  ```
