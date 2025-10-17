---
mode: agent
---

## 任务目标

创建一个新的数据可视化功能，用于在前端“统计”页面上展示请求日志的关键指标。此功能需要后端提供数据聚合 API，并由前端使用 ECharts 图表库进行可视化呈现。

## 工作流

请遵循以下后端和前端工作流程来完成此任务。

### Part 1: 后端开发

#### 步骤 1: 分析数据结构

1.  **获取数据结构**:
    *   从 `backend/app/services/request_logs/schemas.py` 中的 `RequestLog` 获取最新的日志条目数据结构。
    *   理解每个字段的含义和类型。

#### 步骤 2: 设计图表与数据结构

1.  **规划可视化方案**:
    *   根据 `RequestLog` 数据结构，设计合适的图表类型（如时间序列图、条形图、饼图等）。
    *   确定需要聚合的指标（如请求次数、token 使用量、成本等）。
    *   设计适合前端使用的数据结构，包括时间维度、模型维度和指标维度。

#### 步骤 3: 实现数据库交互层

1.  **更新抽象基类**:
    *   在 `backend/app/services/request_logs/db_manager.py` 中添加合适的抽象方法，定义数据查询接口。

2.  **实现数据库具体实现**:
    *   在 `backend/app/services/request_logs/sqlite_manager.py` 中实现抽象方法，根据 SQLite 特性编写具体的 SQL 查询。
    *   注意设计时考虑未来可能添加的其他数据库类型，保持接口的一致性。

#### 步骤 4: 实现业务逻辑层

1.  **更新请求日志管理器**:
    *   在 `backend/app/services/request_logs/request_log_manager.py` 中实现具体的业务逻辑。
    *   调用数据库层方法获取原始数据，进行业务处理和数据转换。
    *   将数据转换为前端所需的格式。

#### 步骤 5: 创建 API 端点

1.  **更新 `schemas.py` (如果需要)**:
    *   如果新的数据结构无法用现有 schema 表示，请在 `backend/app/api/api/schemas/request_logs.py` 中创建一个新的 Pydantic schema 来定义响应体。
2.  **更新 `request_logs.py`**:
    *   在 `backend/app/api/api/endpoints/request_logs.py` 中，添加一个新的 API 端点（例如 `GET /stats/model-usage`）。
    *   此端点应调用 `request_log_manager` 中新创建的业务逻辑方法。
    *   使用在 `schemas.py` 中定义的 schema（如果已创建）来序列化响应数据。
    *   确保端点受到适当的认证保护。

### Part 2: 前端开发

#### 步骤 1: 创建 API 服务

1.  **更新 `service.ts`**:
    *   在 `frontend/src/lib/features/stats/service.ts` 文件中，添加一个新的函数。
    *   该函数应使用 `api.get()` 向 Part 1 中创建的新后端端点发起请求。
    *   为函数添加正确的 TypeScript 类型定义以匹配 API 响应。

#### 步骤 2: 开发可视化组件

1.  **创建新的 Svelte 组件**:
    *   在 `frontend/src/lib/features/stats/components/` 目录下，创建一个新的 Svelte 组件文件（例如 `ModelUsageChart.svelte`）。
    *   **参考 `UsageTrendChart.svelte`**: 以该组件为模板，学习其结构、数据获取方式和图表配置。
    *   **集成 ECharts**: 使用 `svelte-echarts` 库来渲染图表。
    *   **获取数据**: 在组件的 `script` 部分，调用 `service.ts` 中新创建的 API 服务函数来获取数据。
    *   **配置图表**: 根据获取的数据，配置 ECharts 的 `option` 对象，以创建有意义的可视化（例如，堆叠条形图或折线图）。
    *   **UI/UX**: 确保组件具有加载状态和错误状态处理，并遵循 DaisyUI 的设计风格。

#### 步骤 3: 集成到页面

1.  **更新 `+page.svelte`**:
    *   打开 `frontend/src/routes/stats/+page.svelte` 文件。
    *   导入刚刚创建的 `ModelUsageChart.svelte` 组件。
    *   在页面的适当位置将组件实例化，使其显示在统计页面上。

## 验收标准

1.  后端成功创建了一个新的 API 端点，该端点能够返回按需聚合的请求日志数据。
2.  前端创建了一个新的可重用图表组件。
3.  统计页面 (`/stats`) 成功加载并显示了新的数据可视化图表。
4.  图表能正确反映后端数据库中的日志数据。
5.  代码遵循项目现有的编码规范和风格。