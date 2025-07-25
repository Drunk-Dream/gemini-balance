# 项目信息

## 项目背景与目标
本项目旨在开发一个基于 Python FastAPI 的 Google Gemini API 请求转发服务。其核心目标是提供一个中间层，能够接收符合 Google Gemini API 格式的请求，并将其无缝转发至 Google Gemini 官方 API，然后将接收到的响应原样返回给客户端。这包括对普通响应和流式响应的全面支持，确保转发服务具备原 API 的所有功能。

## 用户价值
*   **简化集成**: 为客户端提供统一的访问入口，无需直接处理 Google Gemini API 的复杂性。
*   **增强控制**: 允许在转发层实现额外的逻辑，如请求限速、认证、日志记录、负载均衡等（未来扩展）。
*   **安全性**: 集中管理 API 密钥，减少客户端直接暴露密钥的风险。
*   **灵活性**: 支持流式响应，满足不同应用场景的需求。

## 核心系统架构
本项目采用分层架构，主要模块包括：
*   **前端层**: 使用 Svelte 构建用户界面，用于展示日志信息和 API Key 状态，并提供未来的 Key 管理功能。前端静态文件由后端 FastAPI 提供服务。
*   **API 层**: 使用 FastAPI 定义 RESTful API 端点，负责接收和验证客户端请求。`generateContent` 和 `streamGenerateContent` 端点已统一由 `GeminiService.generate_content` 方法处理，并移除了对 `stream` 查询参数的直接依赖。同时，引入了 `ApiService` 作为基类，象了通用的 API 交互逻辑，并重构了 `OpenAIService` 和 `GeminiService` 以继承此基类。新增了 `/api/status/keys` 和 `/api/status/logs` 端点，用于获取 API Key 状态和日志信息。
*   **服务层**: 封装与 Google Gemini API 的交互逻辑，处理请求转发和响应解析。`GeminiService` 现在统一处理内容生成和流式内容生成，并增加了对函数调用（Function Calling）和工具使用（Tool Usage）的支持。此外，引入了 `KeyManager` 服务，用于管理和轮询 Google API 密钥，并增强了错误处理机制，包括 API 密钥冷却、指数退避和失败阈值 (`API_KEY_FAILURE_THRESHOLD`)。
*   **核心配置层**: 管理应用配置和日志设置。新增了 `DEBUG_LOG_ENABLED` 和 `DEBUG_LOG_FILE` 配置项，用于控制和指定调试日志的输出，并增加了 API 密钥冷却时间配置 (`MAX_COOL_DOWN_SECONDS`)。
*   **日志管理**: 引入了结构化的日志系统，包含主应用日志 (`app_logger`)、事务日志 (`transaction_logger`) 和可选的调试日志 (`debug_logger`)。日志配置已移至模块级别，`setup_logging` 函数不再是必需的。调试日志的设置已集中到 `setup_debug_logger` 函数中，并利用 `RotatingFileHandler` 进行日志管理。

## 关键技术栈
*   **后端框架**: FastAPI (Python)
*   **前端框架**: SvelteKit
*   **应服务器**: uvicorn
*   **HTTP 客户端**: httpx (异步 HTTP 请求)
*   **数据验证**: Pydantic，已扩展支持函数调用和工具使用相关的数据模型。
*   **环境变量管理**: python-dotenv
*   **Google Gemini SDK**: google-generativeai (用于与 Gemini API 交互)
*   **异步**: Python `asyncio`
*   **日志**: Python `logging` 模块，支持多日志记录器和可配置的调试日志。
*   **测试**: pytest, pytest-asyncio (用于单元测试)
*   **容器化**: Docker, Docker Compose

## 主要模块关系
*   `Dockerfile`: 定义了用于构建后端应用镜像的说明，包含前端多阶段构建。
*   `docker-compose.yml`: 用于编排和运行多容器应用，包括后端服务和代理服务。
*   `backend/main.py`: 后端应用入口，使用 `uvicorn` 启动 FastAPI 应用，支持通过环境变量配置主机和端口，并挂载前端静态文件。
*   `backend/app/api/v1beta/endpoints/gemini.py`: 定义 API 端点，调用 `GeminiService` 处理请求。
*   `backend/app/api/v1beta/endpoints/status.py`: 定义 API 端点，用于获取 API Key 状态和日志信息。
*   `backend/app/api/v1beta/schemas/gemini.py`: 定义请求和响应的数据模型，包括对函数调用和工具使用的支持。
*   `backend/app/services/base_service.py`: 抽象了通用的 API 交互逻辑，包括 HTTP 客户端设置、请求处理、错误管理和调试日志。
*   `backend/app/services/gemini_service.py`: 核心业务逻辑，负责与 Google Gemini API 进行通信，统一处理内容生成和流式响应，并支持函数调用。
*   `backend/app/services/openai_service.py`: 继承自 `ApiService`，处理 OpenAI API 的请求转发，并支持 `reasoning_effort` 参数。
*   `backend/app/services/key_manager.py`: 管理和轮询 Google API 密钥，处理密钥冷却逻辑，包括指数退避和失败阈值。
*   `backend/app/core/config.py`: 加载和管理应用配置，包括新的日志配置项和 API 密钥冷却时间。
*   `backend/app/core/logging.py`: 配置应用日志系统，提供结构化的日志记录。调试日志的设置已集中到 `setup_debug_logger` 函数中，并利用 `RotatingFileHandler` 进行日志管理。
*   `v2raya`: 作为网络代理服务，在 `docker-compose.yml` 中配置，用于处理后端服务的网络请求。

## 重要设计模式
*   **分层架构**: 将应用逻辑划分为 API、服务和核心配置层，提高模块化和可维护性。
*   **服务抽象**: 引入 `ApiService` 作为基类，抽象通用 API 交互逻辑，减少代码重复。
*   **依赖注入**: FastAPI 内置的依赖注入机制将用于管理服务和配置的依赖关系。
*   **异步编程**: 利用 Python 的 `async/await` 语法处理 I/O 密集型操作，提高并发性能。
*   **函数调用/工具使用**: 支持通过 Pydantic 模型和 Gemini API 进行函数调用和工具使用。
*   **API 密钥轮询冷却**: 引入 `KeyManager` 实现 API 密钥的轮询使用和失败后的冷却机制，提高 API 调用的可靠性。
*   **容器化部署**: 通过 Docker 和 Docker Compose 实现应用的快速部署和环境一致性，并集成了 `v2raya` 作为网络代理。
*   **前后端一体化部署**: 前端静态文件由后端 FastAPI 托管，简化部署和规避跨域问题。
