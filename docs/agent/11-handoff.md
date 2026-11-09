---
owner: 项目开发者
last_updated: 2026-11-06
status: active
read_when: 切换会话、换 agent、让新 agent 接手任务时
---

# 11 · 新会话交接

> 目标：让新 agent 在 **3 分钟**内知道“项目是什么、现在到哪、我要做什么、不能做什么”，不用把 `docs/` 全读。

## 0. 当前快照（2026-11-06）

| 项 | 状态 |
|---|---|
| 阶段 | M0 → **M0.5 11.12 初步 demo** |
| 仓库 | https://github.com/plmt3742/IJieDong（main 分支已推送；最新提交见 git log） |
| 代码 | 无业务代码；只有目录骨架与占位 README |
| 文档 | `docs/agent`、`docs/product`、`docs/adr` 已建；B-001 已记录；内链检查通过；新增 13~20、ADR-005、三类工作流、费用调研、B-002 委派计划 |
| 页面地图 | `docs/product/ue/page-map.html`：18 页线框/29 跳转/可缩放点击/导出 PNG；验证 0 console errors |
| 线框总览 | `docs/product/ue/wireframes.html`：18 张灰度线框/18 个地图链接 |
| 目录 | `apps/services/packages/...` 目录与 `.gitkeep` 已建；业务代码未开始 |
| Git | `main @ 3bdea54`；已推送 `origin/main`；工作区 clean |
| 工作方式 | 非简单任务先写工作包，再委派 subagent；主 agent 审查/集成/复跑验证 |
| 用户/入口 | **公职人员**；原生微信小程序；后续接粤政易工作台；粤政易等程序搭建完再接入 |
| 数据 | 来源支持 **Excel/接口/手工**；当前只有空白 xls 模板；真实样例待提供 |
| 技术栈 | **原生微信小程序 + Vue3 后台 + FastAPI + SQLite(demo)/PostgreSQL(prod) + DeepSeek API + ECharts** |
| 数据模型 | Proposed：区域/指标/数据值规范化；见 ADR-002 |
| Agent | Proposed：只读工具 + ChartSpec；见 ADR-003；LLM 见 14 |
| 部署 | 11.12 本地进程；生产 Docker/PostgreSQL 后置；见 ADR-004 |
| 下一步 | 按 `20-b002-delegation-plan.md` 委派 WP-BE1，再按依赖推进；按 `15-demo-plan-1112.md` 验收 |
| 最大风险 | 6 天截止过紧、原生小程序图表、真实数据/Key/AppID 未到、单人范围过大 |

## 1. 最小启动提示词（复制即用）

```text
你是 i揭东项目的开发 agent。请先按顺序读：
1. AGENTS.md
2. docs/agent/00-context.md
3. docs/agent/04-tasks.md
4. docs/agent/05-architecture.md 的「2 技术栈」「5 数据模型」「6 API v0」「7 Agent 设计」
5. docs/agent/20-b002-delegation-plan.md

读完不要立刻写代码。先用 5 行总结：
- 项目一句话
- 当前阶段/批次
- 你理解的任务 ID 与验收标准
- 关键约束（技术栈/不做什么）
- 你看到的最大风险

然后给我一个 3–5 步计划；非简单任务先拆工作包，再委派 subagent，主 agent 负责集成与复跑验证。

当前任务：<任务 ID + 一句话>
范围：<只改哪些目录/文件>
不做：<明确排除项>
验收：<可验证标准>
```

## 2. 角色提示词

### 2.1 后端任务

```text
你是本项目后端 agent（Python 3.13 + FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL）。
先读：AGENTS.md → 00-context.md → 04-tasks.md → 05-architecture.md 的「2/5/6/9 节」→ 06-file-tree.md → 09-risks.md 的数据/安全节。

任务：<BE-xxx / DATA-xxx>。
只改 services/api/ 下与任务相关的文件；不改前端/Resource。
接口/字段/错误码必须与 05 一致；改了就先更新 05 和 OpenAPI。
LLM 测试用 mock，不花真实额度；不在测试里连真实数据库（用测试库/事务回滚）。
完成后跑 uv run ruff check + uv run pytest，并在批次记录里贴结果。
先复述任务和计划，等我确认再写代码。
```

### 2.2 Web 后台任务

```text
你是本项目后台 agent（Vue3 + Vite + TS + Element Plus + ECharts + Pinia）。
先读：AGENTS.md → 00-context.md → 04-tasks.md → 05-architecture.md 的「6 API」→ 06-file-tree.md → docs/product/03-page-specs.md。

任务：<FE-xxx>。
只改 apps/admin/ 下与任务相关的文件；不改后端/小程序/Resource。
接口以 05 为准；没有的接口先用 mock，不要自己发明字段。
页面必须有 loading/empty/error 三态；表格/表单/图表要有空数据兜底。
完成后跑 pnpm lint / typecheck / build，并在批次记录里贴结果。
先复述任务和计划，等我确认再写代码。
```

### 2.3 原生微信小程序任务

```text
你是本项目移动端 agent（原生微信小程序 + TypeScript + TDesign Miniprogram + echarts-for-weixin）。
先读：AGENTS.md → 00-context.md → 04-tasks.md → 05-architecture.md 的「6 API/7 ChartSpec」→ 06-file-tree.md → docs/product/02-ia-and-flows.md + 04-data-catalog.md。

任务：<MP-xxx>。
只改 apps/mp/ 下与任务相关的文件；不改后端/后台/Resource。
接口以 05 为准；没有的接口先用 mock。
图表用 ChartSpec 渲染器，不直接写 ECharts option；不做 H5。
必须用微信开发者工具验证：首页/页面可打开、请求可达、图表可渲染。
空/错/loading/无数据要有兜底；弱网可重试。
完成后跑 lint/typecheck（如有）并在微信开发者工具截图/记录，在批次记录里贴结果。
先复述任务和计划，等我确认再写代码。
```

### 2.4 AI/Agent 任务

```text
你是本项目 AI agent（Python + OpenAI 兼容 API + 工具调用 + Pydantic 校验）。
先读：AGENTS.md → 00-context.md → 04-tasks.md → 05-architecture.md 的「7 Agent 设计/8 ChartSpec」→ ADR-003 → 09-risks.md 的 AI 节。

任务：<AI-xxx>。
只改 services/api/app/ai/ 和相关 schemas/tests；不改前端/Resource。
LLM 只能调用白名单工具；不允许生成 SQL/JS/任意代码；不允许直连数据库。
输出必须过 Pydantic + ChartSpec 校验；无数据必须拒答，不补 0。
测试用 mock LLM；评测集不含真实敏感数据。
完成后跑 ruff + pytest，并在批次记录里贴评测结果。
先复述工具清单/输出契约/失败兜底，等我确认再写代码。
```

### 2.5 文档/需求任务

```text
你是本项目文档/需求 agent。先读：AGENTS.md → 00-context.md → 01-project.md → 12-open-questions.md → docs/README.md。

任务：<DOC-xxx>。
只改 docs/ 下与任务相关的文件；不改代码/Resource。
新增结论必须能追溯到材料/代码/决策；不确定的写进 12-open-questions，不要猜。
更新文档后同步 04-tasks / 08-batch-log / 11-handoff。
先复述“已知/未知/建议”，等我确认再写。
```

### 2.6 Debug 任务

```text
你是本项目 debug agent。先读：AGENTS.md → 09-risks.md 对应条目 → 05-architecture.md → 相关代码。

现象：<复现步骤/期望/实际/环境/日志>
先定位根因，不要随机改。一次只改一个假设；每轮说明“改了什么/为什么/怎么验证”。
不要删除失败测试；不要用 as any/@ts-ignore/# type: ignore 掩盖问题。
修完补一个能复现的测试，并跑相关测试/构建。
```

### 2.7 Review 任务

```text
你是本项目 review agent。先读：07-workflow.md 的「自审清单」+ 05-architecture.md。

审查范围：<PR/commit/diff>。
只看：逻辑/边界、权限、密钥、API 契约、N+1、前端四态、测试、目录规范。
不要改代码；输出按 P0/P1/P2 分级，每条给文件/行号/建议。
```

## 3. 交接时必须提供的信息

| 项 | 示例 | 为什么 |
|---|---|---|
| 任务 ID | `DATA-005` | agent 能在 `04-tasks.md` 找到验收标准 |
| 一句话目标 | “原始 Excel 模板可导入并输出错误报告” | 防止扩大范围 |
| 范围 | “只改 `services/api/app/services/import_service.py` 和测试” | 防止乱改 |
| 明确不做 | “不改前端、不做地图、不做 SSO” | 防止范围蔓延 |
| 验收标准 | “1609 行模板可导入；错误行有 row/column/code” | agent 知道何时停 |
| 相关文件 | 数据目录、接口、样例 | 减少搜索 |
| 已知风险 | “玉滘/玉窖名称不一致” | 避免踩坑 |
| 截止 | 批次结束前 | 决定取舍 |

## 4. 交接检查清单

- [ ] `04-tasks.md` 状态已更新。
- [ ] `08-batch-log/` 最新批次已写“下一步”。
- [ ] `11-handoff.md` 的当前快照已更新。
- [ ] 未提交的改动有说明（分支/文件/原因）。
- [ ] 已知阻塞写在 `12-open-questions.md` / `04-tasks.md` 阻塞区。
- [ ] 没有密钥/真实敏感数据留在工作区。

## 5. 不要让 agent 做的事

- 不要修改 `Resource/`（只读、gitignore）。
- 不要提交 `.env`、API Key、JWT Secret、数据库密码、微信 AppSecret。
- 不要让 LLM 直连数据库或生成 SQL/JS。
- 不要扩大 P0 范围；不要加地图/大屏/SSO/多租户（除非任务明确）。
- 不要凭记忆写 API；以 `05-architecture.md` / OpenAPI 为准。
- 不要删除失败测试来“通过”。
- 不要一次把 `docs/` 全读；按 `docs/agent/README.md` 的路由读。
- 不要新建顶层目录；按 `06-file-tree.md` 放文件。
- 不要把 xls 空值当 0；不要用模糊匹配解决区域名称不一致。
- 不要跳过规划直接写代码；非简单任务先拆工作包并委派 subagent，主 agent 复跑验收。
- 不要在工程文档或 README 中使用 emoji。
