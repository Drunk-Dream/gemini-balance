# 前端与后端功能开发任务清单

## 阶段一：项目重构与后端基础建设

- [ ] **项目结构调整**
    - [x] 将所有现有后端代码（`app`, `tests`, `Dockerfile` 等）移动到新的 `backend/` 目录中。
    - [ ] 创建 `frontend/` 目录，用于存放 Svelte 前端项目。
    - [ ] 更新 `docker-compose.yml` 和 `backend/Dockerfile` 中的路径，以适应新的目录结构。
    - [ ] 调整 `.gitignore` 文件，添加前端相关的忽略项（如 `frontend/node_modules`）。

- [ ] **KeyManager 功能增强**
    - [ ] 在 `KeyManager` 中为每个 key 增加用量统计功能，例如记录今日调用次数。
    - [ ] 考虑将 key 的状态（包括用量、冷却时间等）持久化，以防服务重启后数据丢失（初期可先用内存存储，后续再优化）。

- [ ] **新增后端 API**
    - [ ] 创建 `GET /api/status/keys` 端点：返回所有 API key 的详细状态列表，包括 `key` 的部分信息（出于安全，不应返回完整 key）、是否可用、今日用量、冷却状态及剩余时间。
    - [ ] 创建 `GET /api/status/logs` 端点：提供查看日志文件的功能。可以考虑分页或返回最新的 N 条日志。
    - [ ] (可选) 为日志查看功能实现 WebSocket，以便实时将新日志推送到前端。

## 阶段二：前端界面实现

- [ ] **Svelte 项目初始化**
    - [ ] 在 `frontend/` 目录下初始化一个 SvelteKit 项目。
    - [ ] 集成 TailwindCSS 并完成基础配置。

- [ ] **前端页面开发**
    - [ ] 创建一个统一的仪表盘布局（Dashboard Layout）。
    - [ ] **Key 状态监控页面**
        - [ ] 调用 `GET /api/status/keys` API 获取数据。
        - [ ] 将数据显示在一个表格或卡片列表中。
        - [ ] 实现定时刷新或通过 WebSocket 实时更新数据。
    - [ ] **日志查看页面**
        - [ ] 调用 `GET /api/status/logs` API 或通过 WebSocket 连接获取日志。
        - [ ] 创建一个可滚动的日志展示窗口。
        - [ ] (可选) 添加日志级别筛选、关键词搜索等功能。

## 阶段三：集成、测试与部署

- [ ] **前后端集成**
    - [ ] 在开发环境中配置 Vite 的代理，将前端的 `/api` 请求转发到 FastAPI 后端。
    - [ ] 配置 FastAPI 提供静态文件服务，用于在生产环境中托管构建好的前端应用。
    - [ ] 更新 `docker-compose.yml`，使其能够同时构建和运行前端与后端服务。

- [ ] **测试**
    - [ ] 为新增的后端 API 编写单元测试。
    - [ ] 进行端到端的手动测试，确保前后端数据交互正常。

- [ ] **文档更新**
    - [ ] 更新 `README.md` 和 `.clinerules/memory/project_info.md`，补充关于前端功能和新 API 的说明。
