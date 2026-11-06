# ADR-001: 技术栈

- 状态：Accepted（移动端选型已由 ADR-005 更新；其余仍有效）
- 日期：2026-11-06
- 决策人：项目开发者
- 相关任务：B-002、DOC-006
- 相关文档：`docs/agent/05-architecture.md`、`docs/adr/ADR-005-native-wechat-miniprogram.md`

## 1. 背景

需要同时交付：

1. **原生微信小程序**（用户要求；后续接粤政易工作台）。
2. Web 管理后台（数据导入、编辑、审计、图表预览）。
3. 后端 API + LLM/Agent + 数据查询。
4. 数据可视化（ECharts）。
5. 单人开发、可维护、可部署到普通云/政务外网/信创环境。

约束：不能重运维（不引入微服务/消息队列/Redis 除非必要）；开发期要快；后期要能适配政务外网、ARM64、国产库、私有化 LLM。

## 2. 决策

| 层 | 选型 |
|---|---|
| 小程序 | **原生微信小程序 + TypeScript + TDesign Miniprogram + echarts-for-weixin**（见 ADR-005） |
| Web 后台 | **Vue 3 + Vite + TypeScript + Element Plus + ECharts + Pinia + Vue Router** |
| 后端 | **Python 3.13 + FastAPI + Pydantic v2 + SQLAlchemy 2.0 + Alembic** |
| 数据库 | **SQLite（11.12 demo）/ PostgreSQL 16（生产）** |
| LLM | **DeepSeek API（OpenAI 兼容）+ 适配层**；可切 Qwen/GLM/vLLM/Ollama |
| 图表 | **ECharts 5 + 平台无关 ChartSpec** |
| 包管理 | pnpm（Node）+ Python venv/uv |
| 部署 | 11.12 本地进程；生产 Docker Compose + Nginx；GitHub Actions |

## 3. 后果

### 正面

- 原生小程序兼容/性能最好；无额外运行层；后续接粤政易风险低。
- 后台与小程序共享 API 类型、ChartSpec；不共享页面代码（可接受）。
- FastAPI 与 Python 生态适合 LLM/数据处理；OpenAPI 自动生成，前端类型可生成。
- PostgreSQL 稳定、SQLAlchemy 可移植；数据量小，性能足够。
- ECharts 功能完整，后台/H5 成熟；小程序有成熟包装方案。
- 不引入 LangChain/Redis/Celery，降低单人维护成本。

### 负面/代价

- 原生小程序不能复用到 H5；若粤政易强制 H5，需要补薄 H5 壳。
- Python async/sync 边界需要设计；Excel 解析阻塞需线程池/进程池。
- SQLite 只适合演示；生产 PostgreSQL 在信创环境可能需适配金仓/达梦。
- Element Plus 视觉偏传统；政府场景可接受，但需要定制。
- 没有队列，长任务（大文件导入/批量 AI）需要限制或后续加 worker。

### 风险与缓解

| 风险 | 缓解 |
|---|---|
| 原生小程序 ECharts 渲染问题 | B-002 早期做 spike；echarts-for-weixin 自定义构建；表格降级 |
| 信创数据库不兼容 | SQLAlchemy 可移植类型；避免 PG 特有语法；预留适配 spike |
| LLM 供应商变化 | OpenAI 兼容适配层；配置化 base_url/model |
| async 复杂度 | 统一 async + asyncpg；若 B-002 验证成本过高，再评估同步回退并记录 ADR |

## 4. 备选方案

| 方案 | 优点 | 缺点 | 为什么没选 |
|---|---|---|---|
| 原生微信小程序 | 兼容/性能最好；少一层运行层 | 不能复用到 H5；样板多 | **已采用（ADR-005）**；当前无 H5 需求 |
| Taro + React | 多端；React 生态 | 运行层/约束；与后台 Vue 不统一 | 当前无多端需求 |
| Spring Boot + Vue | 政务项目常见；稳定 | 开发慢；LLM 生态不如 Python | 单人快速交付优先 |
| Node/NestJS + Vue | 全 TS；类型统一 | LLM/数据生态弱于 Python | AI 是核心需求 |
| MySQL 8 | 政务云常见；运维熟悉 | 与金仓/PG 生态取舍 | PostgreSQL 类型/JSON/分析能力更好；可换 |
| 低代码平台 | 快 | 定制/合规/私有化受限 | 不满足长期维护与粤政易 |

## 5. 实施要点

1. B-002 建立 monorepo：`apps/admin`、`apps/mp`、`services/api`、`packages/*`。
2. 锁定 Node/Python 版本；提交 lockfile；CI 用同一版本。
3. 先做 `/health` + 登录 + 一条数据查询 + 一张图表，验证全链路。
4. 小程序早期验证：微信开发者工具打开、ECharts 渲染、包体、请求。
5. 数据库只使用可移植类型：`NUMERIC`、`TEXT`、`DATETIME`、`JSON`（避免 PG 特有 JSONB 运算符依赖）。
6. LLM 配置：`LLM_PROVIDER=deepseek`、`LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL`、`LLM_TIMEOUT`；代码不写死供应商。

## 6. 复审条件

- 原生小程序无法满足 11.12 主路径 → 按 `15-demo-plan-1112.md` 砍范围或评估 H5 壳。
- 粤政易强制 H5 → 补薄 H5 壳或重评跨端框架。
- 需求方强制 Java/MySQL/国产库/国产 OS → 重新评估后端/数据库。
- 并发/数据量超过预期（如 >100 万行、>100 并发）→ 评估异步/缓存/读写分离。
- LLM 必须私有化且 OpenAI 兼容层不满足 → 评估专用 SDK/本地部署。
- B-002 脚手架 3 天内无法跑通全链路 → 缩小技术栈（先 H5 + 后台，小程序后置）。

## 7. 链接

- `docs/agent/05-architecture.md`
- `docs/agent/06-file-tree.md`
- `docs/agent/09-risks.md` R-009/R-012
- `docs/agent/12-open-questions.md` Q-04/Q-08
