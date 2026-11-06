# i揭东（IJieDong）

> 揭东区政府数据的数字化存储、可视化与智能问答平台。当前处于 **M0：理解与骨架**，仓库以文档和工程约定为主，尚未开始业务代码。

## 一句话

把分散的揭东区、镇街、村居数据，变成一个**可查、可看、可问**的移动数据门户：

```text
数据导入/治理 → 指标浏览与图表 → 自然语言问答 → 带数据依据的图表/答案
```

## 当前状态（2026-11-06）

- ✅ 已分析需求方提供的对接材料（需求问答、数据模板、粤政易入驻指引）
- ✅ 已确认：公职人员；原生微信小程序；粤政易等程序搭建完再接；数据来源 Excel/接口/手工；DeepSeek API；11.12 前 demo+文档+成本
- ✅ 已建立 agent 工程文档体系与批次开发记录机制
- ✅ 已完成双线工程：费用调研、三类工作流、目录骨架、18 页低保真页面结构地图
- ✅ 文档内链检查通过；本地 git 已初始化并关联 origin（尚未提交）
- ⬜ 尚未创建可运行代码；下一步是 **B-002 11.12 demo 冲刺**
- 📅 11.12 计划：[docs/agent/15-demo-plan-1112.md](docs/agent/15-demo-plan-1112.md)
- 🗺️ 页面地图：[docs/product/ue/page-map.html](docs/product/ue/page-map.html)（可缩放/点击/导出 PNG）
- 🧩 线框总览：[docs/product/ue/wireframes.html](docs/product/ue/wireframes.html)（18 页灰度线框）
- ⚠️ 仍需确认：玉滘/玉窖、真实样例、DeepSeek 数据密级、粤政易网络/等保、11.12 验收/资源；见 [docs/agent/12-open-questions.md](docs/agent/12-open-questions.md)

## 从这里开始

| 你是 | 先读 |
|---|---|
| 第一次接触项目的人 | [docs/agent/00-context.md](docs/agent/00-context.md) |
| 接手的 AI agent | [AGENTS.md](AGENTS.md) → [docs/agent/README.md](docs/agent/README.md) |
| 想知道现在做什么 | [docs/agent/04-tasks.md](docs/agent/04-tasks.md) + [docs/agent/03-roadmap.md](docs/agent/03-roadmap.md) |
| 想知道需求边界 | [docs/agent/01-project.md](docs/agent/01-project.md) |
| 想改代码/接口/目录 | [docs/agent/05-architecture.md](docs/agent/05-architecture.md) + [docs/agent/06-file-tree.md](docs/agent/06-file-tree.md) |
| 想知道每批次 agent 做了什么 | [docs/agent/08-batch-log/](docs/agent/08-batch-log/) |
| 想查原始资料摘要 | [docs/agent/10-resources.md](docs/agent/10-resources.md) |
| 想看三类工作流 | [docs/agent/18-workflows.md](docs/agent/18-workflows.md) |
| 想查费用调研 | [docs/agent/19-cost-research.md](docs/agent/19-cost-research.md) |
| 想看页面结构地图 | [docs/product/05-page-structure.md](docs/product/05-page-structure.md) → [docs/product/ue/page-map.html](docs/product/ue/page-map.html) |
| 想逐页看线框 | [docs/product/ue/wireframes.html](docs/product/ue/wireframes.html) |

## 技术栈（已确认方向，B-002 验证）

| 层 | 选型 | 说明 |
|---|---|---|
| 移动端 | **原生微信小程序 + TypeScript + TDesign Miniprogram + echarts-for-weixin** | 不做 H5；后续接粤政易工作台 |
| Web 后台 | Vue 3 + Vite + TypeScript + Element Plus + ECharts | 数据管理、导入、审计、图表预览 |
| 后端 | Python 3.13 + FastAPI + SQLAlchemy 2.0 + Alembic | 同步/异步边界见架构文档 |
| 数据库 | **SQLite（11.12 demo）/ PostgreSQL 16（生产）** | 同一模型；生产按需求方资源适配 |
| LLM/Agent | **DeepSeek API（OpenAI 兼容）** + 工具调用 | 可切 Qwen/GLM/vLLM/Ollama/政务云；不写死 |
| 图表 | ECharts 5 + 平台无关 `ChartSpec` | LLM 只产出受约束的图表意图，不生成任意 JS |
| 部署 | 11.12 本地进程；生产 Docker Compose + Nginx | 预留 ARM64/政务外网部署 |

决策依据见 [docs/adr/](docs/adr/)。

## 目录结构（规划）

```text
IJieDong/
├── apps/
│   ├── admin/          # Web 管理后台
│   └── mp/             # 原生微信小程序
├── services/
│   └── api/            # FastAPI 后端
├── packages/
│   ├── contracts/      # OpenAPI 生成的 TS 类型
│   └── chart-spec/     # ChartSpec → ECharts option 适配
├── contracts/          # OpenAPI 契约与示例
├── deploy/             # Docker Compose / Nginx / 环境说明
├── scripts/            # 跨端脚本
├── docs/               # agent / product / adr 三层文档
├── Resource/           # 本地原始资料，gitignore，不进仓库
├── learning/           # 本地学习笔记，gitignore
└── tools/              # 本地工具，gitignore
```

详细目录职责与放置规则见 [docs/agent/06-file-tree.md](docs/agent/06-file-tree.md)。

## 本地专用目录（不进 Git）

- `Resource/`：需求方原始材料（doc/xls/rar/pdf），只读，不上传。
- `learning/`：个人学习笔记、临时验证。
- `tools/`：本地脚本/工具，不进入产品交付物。
- `.obsidian/`：本地 Obsidian 配置。
- `.omo/`：本地 agent 运行状态，不进仓库。

> 这些目录已写入 `.gitignore`；不要把其中的原文大段复制进 `docs/`，只放摘要与链接。

## 重要边界

- 本仓库当前是**个人开发项目**，无多人协作流程；但保留分支、批次记录和自检清单，保证可交接。
- 粤政易/等保/信创属于**后置合规阶段**，不阻塞 MVP 开发，但会影响架构与部署选择。
- 任何 API Key、数据库密码、JWT Secret 不得进入仓库；只提交 `.env.example`。

## 变更记录

| 日期 | 变更 |
|---|---|
| 2026-11-06 | 初始化文档体系、技术栈草案、数据模型与 Agent 架构；建立批次开发记录 |
