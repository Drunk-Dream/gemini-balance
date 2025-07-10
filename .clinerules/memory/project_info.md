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
*   **API 层**: 使用 FastAPI 定义 RESTful API 端点，负责接收和验证客户端请求。
*   **服务层**: 封装与 Google Gemini API 的交互逻辑，处理请求转发和响应解析。
*   **核心配置层**: 管理应用配置和日志设置。

## 关键技术栈
*   **后端框架**: FastAPI (Python)
*   **HTTP 客户端**: httpx (异步 HTTP 请求)
*   **数据验证**: Pydantic
*   **环境变量管理**: python-dotenv
*   **Google Gemini SDK**: google-generativeai (用于与 Gemini API 交互)
*   **异步**: Python `asyncio`

## 主要模块关系
*   `app.main`: 应用入口，初始化 FastAPI 应用并注册路由。
*   `app.api.v1.endpoints.gemini`: 定义具体的 API 路由，接收请求并调用服务层。
*   `app.api.v1.schemas.gemini`: 定义请求和响应的数据模型，确保数据格式的正确性。
*   `app.services.gemini_service`: 核心业务逻辑，负责与 Google Gemini API 进行实际通信。
*   `app.core.config`: 加载和管理应用配置。
*   `app.core.logging`: 配置应用日志系统。

## 重要设计模式
*   **分层架构**: 将应用逻辑划分为 API、服务和核心配置层，提高模块化和可维护性。
*   **依赖注入**: FastAPI 内置的依赖注入机制将用于管理服务和配置的依赖关系。
*   **异步编程**: 利用 Python 的 `async/await` 语法处理 I/O 密集型操作，提高并发性能。

## 日志管理
*   采用 Python 标准 `logging` 模块，配置日志级别、格式和输出目标。
*   关键请求和响应信息、错误和异常将记录到日志中，便于问题排查和监控。
