---
owner: 项目开发者
last_updated: 2026-11-10
status: planned
read_when: 开始 B-002 代码冲刺；给 subagent 分配任务；会话交接
---

# 20 · B-002 子代理委派计划

> 目标：在 2026-11-12 前完成演示闭环。  
> 原则：先规划、再委派 subagent、主 agent 集成与验收；子代理不得直接提交或推送。  
> 本文件是计划，不代表代码已实现。

> 本计划是 `AGENTS.md` 硬规则 12/13 与 `07-workflow.md` §2.4 的具体实例：非简单任务必须规划并委派 subagent，后续批次沿用同一规则。质量优先：可并行的独立工作包优先并行；主 agent 审查 diff 并复跑验证；子代理自述不作为完成依据。

## 1. 目标与边界

### 1.1 目标

- Excel/演示数据落 SQLite。
- 原生微信小程序：首页、区域、指标、基础图表。
- DeepSeek 问答：数值、排名、对比，返回答案、ChartSpec、引用。
- 最小后台：登录、数据列表、导入。
- 文档、费用评估、演示脚本。

### 1.2 不做

- 粤政易 SSO、工作台入口。
- 地图、大屏、导出、多年趋势。
- 完整 RBAC、审核流、多用户。
- Docker/PostgreSQL 生产部署。
- 完整测试、压测、等保/信创整改。

### 1.3 约束

- 所有接口以 `docs/agent/05-architecture.md` 为准。
- 不修改 `Resource/`；不提交密钥；不新增顶层目录。
- 共享文件由主 agent 统一修改，子代理只改自己工作包内的文件。
- 子代理输出必须由主 agent 复跑验证，不能以子代理自述作为完成依据。

## 2. 工作包

| ID | 工作包 | 建议 category | 建议 skills | 依赖 | 主要交付 |
|---|---|---|---|---|---|
| WP-BE1 | 后端基础 | deep-low | backend-patterns, api-design | 无 | FastAPI 脚手架、SQLite、`/health`、配置/日志、测试 |
| WP-DATA1 | 数据模型与导入 | deep-low | backend-patterns, api-design | WP-BE1 | 数据表/迁移、227 区域/15 指标种子、Excel 导入、查询/排名/对比 API |
| WP-MP1 | 原生小程序 | visual-engineering | frontend-patterns, frontend-design | WP-BE1（可先用 mock） | 首页、区域、指标、图表、request 封装 |
| WP-ADMIN1 | 最小后台 | visual-engineering | frontend-patterns, frontend-design | WP-BE1（可先用 mock） | 登录、数据列表、导入页、后台壳 |
| WP-AI1 | AI 问答 | deep-low | api-design, backend-patterns | WP-DATA1 | DeepSeek 客户端、工具、Agent 循环、ChartSpec 校验、问答 API |
| WP-INT1 | 集成与验收 | 主 agent | 无 | 全部 | 端到端联调、演示数据、文档/成本、演示脚本 |

## 3. 文件归属

| 工作包 | 只改这些路径 | 不要改 |
|---|---|---|
| WP-BE1 | `services/api/pyproject.toml`、`requirements.txt`、`.env.example`、`app/main.py`、`app/core/**`、`app/db/**`、`app/models/base.py`、`app/api/v1/health.py`、`tests/unit/test_health.py` | 业务模型、前端、`Resource/` |
| WP-DATA1 | `app/models/{region,indicator,data_value,import_job,audit}.py`、`app/schemas/{region,indicator,data_value,import_job}.py`、`app/services/import_service.py`、`app/api/v1/{regions,indicators,data}.py`、`scripts/seed_demo.py`、`tests/{unit,api}/test_data*.py`、`alembic/versions/**` | `app/core`、`app/db`、前端、`Resource/` |
| WP-MP1 | `apps/mp/**` | 后端、后台、`packages/chart-spec`、`Resource/` |
| WP-ADMIN1 | `apps/admin/**` | 后端、小程序、`Resource/` |
| WP-AI1 | `app/ai/**`、`app/schemas/ai.py`、`app/api/v1/ai.py`、`tests/{unit,api}/test_ai*.py` | 前端、数据模型、`Resource/` |
| WP-INT1 | 根 `docs/`、`scripts/`、`contracts/`、集成相关文件 | 子代理未完成的业务文件 |

共享文件由主 agent 修改：

- `services/api/app/models/__init__.py`
- `services/api/app/api/v1/router.py`
- `contracts/openapi.json`
- `docs/agent/05-architecture.md`（契约变化时）
- `docs/agent/04-tasks.md`、`08-batch-log/`、`11-handoff.md`

## 4. 依赖与合并顺序

```text
WP-BE1
  ↓
WP-DATA1 ──→ WP-AI1
  ↓             ↓
WP-MP1 ────────┘
WP-ADMIN1 ─────┘
  ↓
WP-INT1
```

- WP-BE1 必须先完成，其他工作包才有稳定启动方式。
- WP-DATA1 完成数据模型/查询 API 后，WP-AI1 才能接真实工具。
- WP-MP1 与 WP-ADMIN1 可在 WP-BE1 后并行，先用 mock，接口稳定后再切换。
- WP-INT1 由主 agent 最后执行，负责合并、联调、验收、文档和演示。

## 5. 子代理提示词模板

每次委派必须包含以下字段：

```text
TASK:
  一句话任务 + 任务 ID（如 WP-DATA1）。

WORK PACKAGE:
  工作包 ID 与交付物。

FILES YOU OWN:
  只允许修改的目录/文件。

FILES YOU MUST NOT TOUCH:
  明确禁止修改的目录/文件。

GOAL:
  完成后什么变得可用。

ACCEPTANCE:
  可验证标准，逐条列出。

MUST DO:
  必做步骤、必须遵守的契约、必须跑的测试/构建。

MUST NOT DO:
  禁止事项（Resource、密钥、越界改文件、直接 commit/push、删除测试等）。

CONTEXT:
  必读文档、数据模型、API、已有代码、样例数据。

VERIFY:
  需要贴出的命令输出/截图/结果。

HANDOFF:
  完成后返回：改动文件、验证结果、未完成项、风险。
```

委派示例：

```text
TASK: WP-DATA1 数据模型与导入
FILES YOU OWN: services/api/app/models/{region,indicator,data_value,import_job,audit}.py、app/schemas/...、app/services/import_service.py、app/api/v1/{regions,indicators,data}.py、scripts/seed_demo.py、对应 tests、alembic/versions/**
FILES YOU MUST NOT TOUCH: app/core/**、app/db/**、apps/**、Resource/**、根 docs（除任务要求的交付说明）
GOAL: 原始 Excel 模板可导入 SQLite，区域/指标/数据数据可查询。
ACCEPTANCE: 227 区域、15 指标；1608 行模板可导入；重复导入 upsert；错误报告含行/列/错误码；查询/排名/对比 API 有测试。
MUST DO: 先读 05-architecture §5/§6/§4；使用 SQLAlchemy 2.0；空值不写 0；区域别名处理玉滘/玉窖；跑 ruff + pytest。
MUST NOT DO: 不改 app/core、app/db、前端；不引入 pandas；不删除失败测试；不提交密钥；不 commit/push。
CONTEXT: docs/agent/05-architecture.md、docs/product/04-data-catalog.md、services/api/README.md。
VERIFY: 贴 pytest 输出、导入统计、3 条查询示例。
HANDOFF: 返回改动文件、测试结果、未完成项、风险。
```

## 6. 验收矩阵

| 工作包 | 命令/方式 | 通过标准 |
|---|---|---|
| WP-BE1 | `python -m uvicorn app.main:app --reload`；`curl /health`；`ruff check`；`pytest` | 服务启动；`/health` 200；SQLite 可连；lint/test 通过 |
| WP-DATA1 | `pytest`；导入原始模板；SQL 计数 | 227 区域/15 指标；1608 行；错误报告；重复导入 upsert |
| WP-MP1 | 微信开发者工具打开；首页/区域/指标/图表 | 页面可打开；请求可达；图表可渲染；空/错/loading |
| WP-ADMIN1 | `pnpm lint/typecheck/build`；浏览器手动 | 登录；数据列表；导入页；无控制台错误 |
| WP-AI1 | `pytest`（mock LLM）；3 个真实/样例问题 | 工具调用；答案+引用；ChartSpec 合法；无 Key 入库 |
| WP-INT1 | `15-demo-plan-1112.md` §6 验收 | 主路径 3/3；文档/成本；无阻塞 bug |

## 7. 时间安排

| 日期 | 工作 |
|---|---|
| 11.06 | 主 agent 写计划；委派 WP-BE1；准备演示数据/接口 |
| 11.07 | WP-BE1 验收；委派 WP-DATA1；WP-MP1/ADMIN1 可启动 mock |
| 11.08 | WP-DATA1 验收；WP-MP1/ADMIN1 接真实 API |
| 11.09 | WP-AI1；图表/问答联调 |
| 11.10 | 主 agent 集成；修接口/字段冲突 |
| 11.11 | 演示数据、文档、成本、录屏 |
| 11.12 | 缓冲、彩排、交付 |

## 8. 风险与处理

| 风险 | 处理 |
|---|---|
| 子代理改共享文件导致冲突 | 共享文件由主 agent 统一改；子代理只改归属文件 |
| 接口字段漂移 | 以 05/OpenAPI 为准；主 agent 在合并时校验 |
| 原生小程序图表包体/兼容 | 早期 spike；echarts-for-weixin 自定义构建；表格降级 |
| DeepSeek Key 未到 | mock/预生成答案；不阻塞 UI/接口 |
| 时间不足 | 按 15-demo-plan §7 砍范围；先保导入/浏览/一个图表/一个问答 |
| 子代理自述完成但未验证 | 主 agent 复跑命令/手动路径；未通过不合并 |

## 9. 交接检查

- [ ] 每个工作包有任务 ID、文件归属、验收标准。
- [ ] 子代理已复述任务与计划。
- [ ] 子代理未改越界文件、未提交/推送。
- [ ] 主 agent 已复跑验证。
- [ ] 已更新 `04-tasks.md`、批次记录、`11-handoff.md`。
- [ ] 文档无 emoji，README 保持正式。

## 10. 2026-11-10 执行状态

| 工作包 | 状态 | 实际产出 |
|---|---|---|
| WP-BE1 | DONE | FastAPI 脚手架、SQLite、健康检查、配置/日志、测试 |
| WP-DATA1 | DONE | 12 张表、migration 0001/0002、227/15/1608 种子、查询 API、Excel 导入 |
| WP-MP1 | DONE（DevTools 待验证） | 原生小程序 10 页 + 3 组件 + ChartSpec Canvas 2D |
| WP-ADMIN1 | DONE | Vue3 后台登录/总览/数据/导入/申请/用户/审计 |
| WP-AI1 | DONE | `/ai/chat` + AnswerBlocks + 10 工具 + 引用 |
| WP-INT1 | DOING | 后端/前端/小程序复跑、主路径联调、文档收口 |
| 新增 WP-AUTH | DONE | JWT/RBAC、申请审批、用户、审计、导入 |
| 新增 WP-EXPORT | DONE | PNG/PDF/XLSX/CSV 导出与 `export_jobs` |

- 子代理均未 commit/push；主 agent 负责最终 diff 审查、验证与提交。
- 共享文件（router、models `__init__`、OpenAPI、05 文档）由主 agent 统一收口。
- 原始 6 天排期已不适用；当前按六步推进，Step 1/2/3/4/5 完成，Step 6 文档收口进行中。
