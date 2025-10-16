---
mode: agent
---

## 任务目标

创建一个新的数据可视化功能，用于在前端“统计”页面上展示请求日志的关键指标。此功能需要后端提供数据聚合 API，并由前端使用 ECharts 图表库进行可视化呈现。

## 工作流

请遵循以下后端和前端工作流程来完成此任务。

### Part 1: 后端开发

#### 步骤 1: 分析与规划

1.  **分析数据库结构**:
    *   仔细阅读 `backend/app/services/request_logs/sqlite_manager.py` 文件。
    *   理解 `request_logs` 表的 schema。
2.  **规划数据模型**:
    *   确定需要为可视化聚合的数据。例如，我们可能需要按天统计不同模型的调用次数、token 消耗量和成本。
    *   设计一个或多个 SQL 查询来实现这种聚合。

#### 步骤 2: 实现数据库交互

1.  **更新 `sqlite_manager.py`**:
    *   在 `backend/app/services/request_logs/sqlite_manager.py` 的 `RequestLogSqliteManager` 类中，添加一个新的异步方法。
    *   该方法应执行在步骤 1 中规划的 SQL 聚合查询。
    *   确保方法包含适当的参数（例如，时间范围）并返回查询结果。
2.  **更新 `db_manager.py`**:
    *   在 `backend/app/services/request_logs/db_manager.py` 的 `RequestLogDBManager` 类中，添加一个新方法。
    *   此方法应调用 `sqlite_manager` 中新创建的方法，以保持数据访问层的一致性。

#### 步骤 3: 实现业务逻辑

1.  **更新 `request_log_manager.py`**:
    *   在 `backend/app/services/request_logs/request_log_manager.py` 的 `RequestLogManager` 类中，创建一个新的业务逻辑方法。
    *   该方法应调用 `db_manager` 的新方法来获取原始聚合数据。
    *   对数据进行处理和转换，使其成为一个适合前端直接使用的、结构化的数据格式（例如，一个包含日期、模型名称和对应统计值的列表）。

#### 步骤 4: 创建 API 端点

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