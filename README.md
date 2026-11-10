# i揭东（IJieDong）

i揭东是面向揭东区公职人员的政府数据门户，目标是将区、镇街、村居三级数据转化为可查询、可展示、可问答的数据服务，并在后续接入粤政易工作台。

当前项目处于 **M0.5 初步演示阶段**。工程文档、技术选型、数据模型、三类工作流、费用调研、目录骨架、页面结构地图、后端 B00~B05 + B08、Web 后台与原生小程序已落地；部署联调、小程序真机验证、AI 50 题评测与真实数据/Key/AppID 仍待收口。

## 1. 项目概述

项目解决以下问题：

1. 政府数据分散在 Excel 模板中，缺少统一的数据底座与更新机制。
2. 区、镇街、村居数据查询依赖人工翻表，效率低。
3. 指标展示以静态表格为主，缺少移动端图表与对比能力。
4. 非数据人员难以自助获取数据，缺少自然语言问答入口。
5. 后续接入粤政易涉及等保、信创、密码评估和政务网络，需要提前预留架构。

项目当前定位为内部数据门户，服务对象为公职人员；公众访问不在本期范围。

## 2. 当前状态

截至 2026-11-10：

- 已完成原始材料分析、数据模板拆解、技术栈与数据模型决策。
- 已完成 agent 工程文档体系、批次记录机制和交接文档。
- 已完成用户工作流、开发工作流、系统工作流。
- 已完成云资源、DeepSeek、小程序认证、域名、SSL、合规测评的费用调研。
- 已完成 `apps/`、`services/`、`packages/` 等目录骨架。
- 已完成 18 页低保真线框、可缩放页面结构地图和 29 条页面跳转。
- 2026-11-10 完成 11.12 决策冻结与契约草案：数据/API、认证/申请、页面设计 v2、AI/AnswerBlocks、组件库、导出；Demo v0 部署到本机工作站并通过局域网/微信小程序实测。
- 后端已落地 B00~B05 + B08：FastAPI/SQLite、12 张表与迁移、227/15/1608 合成种子、只读查询 API、JWT 认证/申请审批/用户/审计/Excel 导入、AI 问答、PNG/PDF/XLSX/CSV 导出；119 tests，OpenAPI 35 paths。
- Web 后台与原生小程序已落地：登录/总览/数据/导入/申请/用户/审计；小程序 10 页 + ChartSpec Canvas 2D。小程序 DevTools/真机待验证。
- 部署资产、CI、根 pnpm workspace 已建立；本机服务器已可局域网访问，云服务器/Docker 保留为后续方案。

当前分支为 `main`，最新提交见 `git log`。

## 3. 建设范围

### 3.1 11.12 初步演示

- Excel 导入与合成演示数据落库；真实数据后续替换。
- 原生微信小程序：首页、区域列表/详情、指标详情、AI 问答、账号申请/审批、导出。
- AI：数值查询、排名、对比、区域画像，返回 AnswerBlocks + 引用；兼容 ChartSpec。
- 可视化 Web 后台：登录、总览、数据列表、导入、申请审批、审计。
- 导出：PNG/PDF/XLSX/CSV，格式由用户选择，不设默认；游客不可导出。
- 技术文档、数据/认证/组件/导出契约、费用评估、对外对接文案。

### 3.2 后续阶段

- 完整数据治理：接口同步、手工录入、导入校验、审计、权限。
- 可视化增强：排名、对比、多年趋势、导出、地图评估。
- AI 问答评测、缓存、限流、问答记录。
- 生产部署：PostgreSQL、Docker、Nginx、HTTPS、备份。
- 粤政易接入：工作台入口、单点登录、无权限友好页、图标、测试报告。
- 等保、信创、密码评估与整改。

### 3.3 本期不包含

- 模型训练或微调。
- 完整 BI 自助分析、实时数据流、多租户。
- 无认证的公众门户或开放 API 平台。
- 未经确认的粤政易上线承诺。

## 4. 技术架构

| 层 | 选型 | 说明 |
|---|---|---|
| 移动端 | 原生微信小程序 + TypeScript + TDesign Miniprogram + echarts-for-weixin | 不做 H5；后续接入粤政易工作台 |
| Web 后台 | Vue 3 + Vite + TypeScript + Element Plus + ECharts | 数据管理、导入、审计、图表预览 |
| 后端 | Python 3.13 + FastAPI + Pydantic v2 + SQLAlchemy 2.0 + Alembic | 契约为先，OpenAPI 输出 |
| 数据库 | SQLite（11.12 演示）/ PostgreSQL 16（生产） | 同一套 SQLAlchemy 模型 |
| LLM | DeepSeek API（OpenAI 兼容）+ 适配层 | 生产可切换政务云或私有化模型 |
| 图表 | ECharts 5 + 平台无关 ChartSpec | LLM 不生成 SQL、JavaScript 或 ECharts option |
| 部署 | 11.12 本机 Windows 工作站（局域网）；生产 Docker Compose + Nginx | 预留 ARM64 与政务外网 |

技术决策依据见 `docs/adr/`。

## 5. 文档体系

| 目录 | 内容 |
|---|---|
| `docs/agent/` | 项目上下文、目标、路线、任务、架构、文件树、工作流、风险、费用、交接 |
| `docs/product/` | PRD、信息架构、页面规范、数据目录、页面结构地图 |
| `docs/adr/` | 架构决策记录 |

工程文档统一使用 Markdown，不使用 emoji；README 保持正式、可对外展示的表述。

## 6. 仓库结构

```text
IJieDong/
├── apps/
│   ├── admin/          # Web 管理后台
│   └── mp/             # 原生微信小程序
├── services/
│   └── api/            # FastAPI 后端
├── packages/
│   ├── contracts/      # OpenAPI 生成的 TypeScript 类型
│   └── chart-spec/     # ChartSpec 与 ECharts 适配
├── contracts/          # OpenAPI 契约与示例
├── deploy/             # Docker、Nginx、环境说明
├── scripts/            # 跨端脚本与文档校验
├── docs/               # agent / product / adr 三层文档
├── Resource/           # 本地原始资料，gitignore
├── learning/           # 本地学习笔记，gitignore
├── tools/              # 本地工具，gitignore
└── AGENTS.md           # agent 入口与硬性约定
```

详细目录职责见 `docs/agent/06-file-tree.md`。

## 7. 里程碑

| 里程碑 | 时间 | 目标 |
|---|---|---|
| M0.5 初步演示 | 2026-11-06 至 2026-11-12 | 可运行 demo、技术文档、费用评估 |
| M1 数据治理与后台 | 11.12 后 | 完整导入/校验、接口/手工、数据管理、审计 |
| M2 可视化与 AI 完善 | 后续 | 对比/排名、图表完善、AI 评测、权限 |
| M3 稳定与部署 | 后续 | 测试、性能、安全、PostgreSQL、Docker、HTTPS |
| M4 粤政易与合规 | 后续 | 工作台入口、SSO、等保、信创、密码评估 |

## 8. 费用与合规

不含人工的现金费用量级如下，详细来源与采购案例见 `docs/agent/19-cost-research.md`。

| 档 | 场景 | 首年现金 |
|---|---|---:|
| 低 | 11.12 演示 / 非密试用 | 0.1 至 0.3 万元 |
| 中 | 等保二级生产（不含密评） | 5 至 13 万元 |
| 高 | 等保三级生产（含密评） | 17 至 34 万元 |

以上不含整改、信创软硬件与迁移、密码产品、人工费用。等保、密评、信创测试通常由需求方或政数部门承担，开发侧负责配合材料与整改。

## 9. 开发与代理流程

后续非简单任务执行以下流程，除 trivial 修改外均为强制：

1. 规划：写清目标、范围、非目标、验收标准、依赖、文件归属与验证方式。
2. 委派：非简单任务必须拆成可独立交付的工作包并委派给 subagent；按工作性质选择 category 与 skills，独立工作包优先并行，明确文件边界，避免冲突。
3. 集成：主 agent 负责审查 diff、合并代码、处理契约变更，并检查是否范围蔓延、是否引入密钥或新依赖、是否同步文档。
4. 验证：主 agent 运行 lint、测试、构建和手动路径，不能仅凭子代理自述判定完成；必要时安排第二轮 review。
5. 留痕：更新任务清单、批次记录、交接文档和 OpenAPI 契约。

工作流细节见 `docs/agent/07-workflow.md`；B-002 的具体工作包见 `docs/agent/20-b002-delegation-plan.md`。

## 10. 安全与合规

- 不在仓库提交 `.env`、API Key、数据库密码、JWT Secret、微信 AppSecret。
- `Resource/` 只读，且不进入 Git；原始材料只做摘要。
- LLM 只调用服务端受控只读工具，不直连数据库，不生成任意 SQL 或 JavaScript。
- 管理端写操作保留审计日志；AI 问答保留调用记录，不记录密钥。
- 粤政易、等保、信创、密码评估按需求和政数部门要求推进，不在未完成测评前宣称合规。
- 本项目为内部项目，未经授权不得对外公开发布或用于生产环境。

## 11. 本地专用目录

以下目录已写入 `.gitignore`：

- `Resource/`：需求方原始材料。
- `learning/`：个人学习笔记与实验。
- `tools/`：本地工具与一次性脚本。
- `.obsidian/`：本地 Obsidian 配置。
- `.omo/`：本地 agent 运行状态。

## 12. 相关链接

- 文档总索引：`docs/README.md`
- Agent 入口：`AGENTS.md`
- 项目速览：`docs/agent/00-context.md`
- 当前任务：`docs/agent/04-tasks.md`
- 页面结构地图：`docs/product/ue/page-map.html`
- 低保真线框：`docs/product/ue/wireframes.html`
- 费用调研：`docs/agent/19-cost-research.md`
- 交接文档：`docs/agent/11-handoff.md`
