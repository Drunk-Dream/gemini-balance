# 项目信息

## 项目背景与目标

本项目旨在开发一个基于 Python FastAPI 的 Google Gemini API 请求转发服务。其核心目标是提供一个具备**用户认证**和**双层密钥管理**的中间层，能够接收符合 Google Gemini API 格式的请求，并将其无缝转发至 Google Gemini 官方 API，然后将接收到的响应原样返回给客户端。这包括对普通响应和流式响应的全面支持，确保转发服务具备高安全性、可管理性和与原生 API 一致的功能。

## 用户价值

- **简化集成**: 为客户端提供统一的访问入口，无需直接处理 Google Gemini API 的复杂性。
- **增强控制**: 允许在转发层实现额外的逻辑，如请求限速、认证、日志记录、负载均衡等（未来扩展）。
- **分级安全**:
  - **用户级 API 密钥**: 用户可通过登录系统，安全地生成、管理和轮换自己的 API 密钥，用于访问本服务。
  - **服务级密钥池**: 集中管理用于请求 Google Gemini 的一组 API 密钥，减少客户端直接暴露密钥的风险。
- **灵活性**: 支持流式响应，满足不同应用场景的需求。
- **用户级 API 密钥调用次数跟踪**: 实时追踪每个用户 API 密钥的使用情况。
- **服务密钥池使用状态可视化**: 提供密钥是否“使用中”的实时状态，优化密钥调度。

## 核心系统架构

本项目采用分层架构，主要模块包括：

- **前端层**: 使用 Svelte 构建用户界面，用于展示日志信息、管理 **Gemini 服务密钥池** (`/status`) 和**用户个人 API 密钥** (`/auth-keys`)。前端已实现响应式布局、登录后自动跳转、统一的密钥添加输入框等功能，优化了用户体验。新增了 `LogViewer` 组件用于日志显示，并对认证密钥管理、登录表单、通知等功能进行了组件化重构。前端静态文件由后端 FastAPI 提供服务。
- **API 层**: 使用 FastAPI 定义 RESTful API 端点。
  - **认证端点 (`/auth`)**: 提供基于 JWT 的用户登录功能。
  - **用户密钥管理端点 (`/auth_keys`)**: 允许认证用户对自己的 API 密钥进行增删改查 (CRUD) 操作，并返回 `call_count` 字段。
  - **服务密钥池管理端点 (`/keys`)**: 允许认证用户管理后端的 Gemini API 密钥池，包括添加、删除和重置密钥状态。
  - **Gemini/OpenAI 代理端点**: 负责接收和验证客户端请求，并转发至相应的服务层。
- **服务层**:
  - **`AuthService`**: 封装用户级 API 密钥的业务逻辑，支持 SQLite 和 Redis 作为后端，并扩展了完整的 CRUD 操作（包括安全密钥哈希、生成、管理、激活/禁用）和 `increment_call_count` 方法。
  - **`GeminiService` / `OpenAIService`**: 继承自通用的 `ApiService` 基类，负责处理对 Google Gemini 和 OpenAI API 的请求转发、函数调用和流式响应。引入了 HTTP 客户端自动重建机制以增强韧性。
- **认证与授权层**:
  - **JWT 认证**: 使用 `python-jose` 和 `passlib` 实现基于密码的登录认证和 JWT 令牌的生成与验证。
  - **依赖注入**: 通过 FastAPI 的 `Depends` 机制，对需要授权的 API 端点强制执行 JWT 令牌验证。`verify_bearer_token` 和 `verify_x_goog_api_key` 现在返回 `AuthKey` 对象。
- **密钥管理层 (服务密钥池)**: 项目的核心特色是其高度模块化和可插拔的**服务密钥池**管理系统。该系统位于 `backend/app/services/key_managers/` 包下，其设计遵循关注点分离原则：
  - **`KeyStateManager`**: 负责核心的 API 密钥状态管理逻辑，包括密钥的获取、归还、冷却、指数退避和失败计数。新增 `is_in_use` 字段以跟踪密钥的实时使用状态。它不直接与任何特定的数据库技术耦合。
  - **`DBManager` (抽象基类)**: 定义了数据库操作的统一接口。
  - **`RedisDBManager` / `SQLiteDBManager` (具体实现)**: 分别实现了 `DBManager` 接口，为 `KeyStateManager` 提供 Redis 或 **异步 SQLite (`aiosqlite`)** 的持久化后端。`SQLiteDBManager` 已调整以正确处理 `is_in_use` 字段。
    系统可以根据环境变量 `DATABASE_TYPE` 动态选择使用哪个数据库后端，实现了密钥管理逻辑与数据存储的解耦。
- **核心配置层**: 管理应用配置和日志设置。新增了 JWT 相关的安全配置，并引入 `REQUEST_TIMEOUT_SECONDS` 使 HTTP 客户端超时可配置。
- **日志管理**: 引入了结构化的日志系统，包含主应用日志 (`app_logger`)、事务日志 (`transaction_logger`) 和可选的调试日志 (`debug_logger`)。

## 关键技术栈

- **后端框架**: FastAPI (Python)
- **前端框架**: SvelteKit
- **异步**: Python `asyncio`, **`aiosqlite`**
- **认证**: **`python-jose[cryptography]`**, **`passlib[bcrypt]`**
- **HTTP 客户端**: httpx
- **数据验证**: Pydantic
- **数据持久化**: Redis, SQLite
- **容器化**: Docker, Docker Compose
- **测试**: pytest, pytest-asyncio

## 主要模块关系

- `backend/app/api/v1beta/endpoints/auth.py`: 定义用户登录和 JWT 令牌颁发端点。
- `backend/app/api/v1beta/endpoints/auth_keys.py`: 定义用户级 API 密钥的 CRUD 端点，现在返回 `call_count`。
- `backend/app/api/v1beta/endpoints/keys.py`: 定义 Gemini 服务密钥池的管理端点。
- `backend/app/api/v1beta/endpoints/gemini.py`: 定义 Gemini API 代理端点。
- `backend/app/core/security.py`: 封装密码哈希、JWT 创建与验证、用户身份验证等安全逻辑。
- `backend/app/services/auth_service.py`: 实现用户级 API 密钥管理的业务逻辑，包含完整的 CRUD 和 `increment_call_count`。
- `backend/app/services/key_managers/key_state_manager.py`: 包含服务密钥池的核心状态管理逻辑，新增 `is_in_use` 字段。
- `backend/app/services/key_managers/sqlite_manager.py`: `DBManager` 的异步 SQLite 实现，使用 `aiosqlite`，已调整 `is_in_use` 处理。
- `frontend/src/routes/login/+page.svelte`: 前端登录页面，已重构为使用 `LoginForm` 组件。
- `frontend/src/routes/auth-keys/+page.svelte`: 前端用户 API 密钥管理页面，已重构为使用 `AddAuthKeyForm` 和 `AuthKeyTable` 组件，并显示 `call_count`。
- `frontend/src/lib/components/logs/LogViewer.svelte`: 新增的日志查看器组件。
- `frontend/src/lib/components/layout/Header.svelte`, `Sidebar.svelte`, `NavLink.svelte`: 响应式布局组件。

## 重要设计模式

- **分层架构**: 将应用逻辑划分为 API、服务、认证和数据持久化等层次。
- **双层密钥管理**:
  - **用户认证密钥**: 用于保护服务接口，确保只有授权用户才能访问。
  - **服务密钥池**: 用于后端服务请求上游 API，对用户透明。
- **JWT (JSON Web Token) 认证**: 提供无状态、可扩展的用户认证机制。
- **依赖注入**: FastAPI 内置的依赖注入机制用于管理服务、配置和安全依赖。
- **异步编程**: 全面利用 `async/await` 和 `aiosqlite` 处理 I/O 密集型操作，提高并发性能。
- **可插拔的持久化密钥管理**: 允许通过配置在 Redis 和 SQLite 之间无缝切换服务密钥池的存储后端。
- **容器化部署**: 通过 Docker 和 Docker Compose 实现应用的快速部署和环境一致性。
- **前后端一体化部署**: 前端静态文件由后端 FastAPI 托管，简化部署和规避跨域问题。
- **用户级 API 密钥调用次数跟踪**: 实现了对用户 API 密钥使用情况的量化追踪。
- **服务密钥池使用状态管理**: 引入了密钥的实时“使用中”状态，优化了密钥的分配和回收。
- **前端组件化与响应式设计**: 通过 Svelte 组件化和响应式布局，提升了前端的用户体验和可维护性。
- **HTTP 客户端韧性与可配置超时**: 增强了 `httpx` 客户端的错误恢复能力，并提供了灵活的超时配置。
- **多模态输入支持**: 扩展了聊天 API，使其能够处理文本、图片和音频等多种输入类型。
