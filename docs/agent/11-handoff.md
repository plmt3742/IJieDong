---
owner: 项目开发者
last_updated: 2026-11-10
status: active
read_when: 切换会话、换 agent、让新 agent 接手任务时
---

# 11 · 新会话交接

> 目标：让新 agent 在 **3 分钟**内知道“项目是什么、现在到哪、我要做什么、不能做什么”，不用把 `docs/` 全读。

## 0. 当前快照（2026-11-10）

| 项 | 状态 |
|---|---|
| 阶段 | M0 → **M0.5 11.12 初步 demo** |
| 仓库 | https://github.com/plmt3742/IJieDong（main 分支已推送；最新提交见 git log） |
| 代码 | B00~B05 + B08 已完成：FastAPI + SQLite + 12 张表 + 迁移 0001/0002/0003 + 227/15/1608 合成种子 + 只读查询 + 认证/申请/审批/导入 + AI 问答/四格式导出（119 tests；OpenAPI 35 paths） |
| 文档 | `docs/agent`、`docs/product`、`docs/adr` 已建；B-001/B-002 已记录；契约 21~25、06/07 已完成；B-003 批次记录已建 |
| 页面地图 | `docs/product/ue/page-map.html` 仍为 v1（18 页/29 跳转），已落后于 06 的 29 页；UI-001 页面地图 v2 待做 |
| 线框总览 | `docs/product/ue/wireframes.html`：18 张灰度线框/18 个地图链接（v1） |
| 目录 | `apps/services/packages/...` 目录与 `.gitkeep` 已建；Web 后台与小程序已落地；`deploy/`、`.github/` 已有资产 |
| Git | 分支 `feat/b002-demo-v0`，已推送 `origin`；最新 `c40acf0`；工作区干净 |
| 工作方式 | 非简单任务必须规划、拆工作包并委派 subagent；主 agent 负责审查 diff、集成与复跑验证；上下文接近 85% 必须先写交接；每批完成后 Git 留档 |
| 用户/入口 | **公职人员**；原生微信小程序；游客/申请/审批最小闭环；后续接粤政易工作台，粤政易等程序搭建完再接入 |
| 数据 | 来源支持 **Excel/接口/手工**；11.12 使用**确定性合成演示数据**覆盖模板全量；真实 Excel 后续提供；GDP 排名不作为 11.12 要求 |
| 技术栈 | **原生微信小程序 + Vue3 后台 + FastAPI + SQLite(demo)/PostgreSQL(prod) + DeepSeek API + ECharts/ChartSpec** |
| 数据模型 | ADR-002 基线 + v2 契约（periods/dimensions/derived/quality/answer_blocks/component_registry/export_jobs）；Demo v0 已建 12 张表，AI/导出字段已由 0003 补齐 |
| Agent | 只读工具 + AnswerBlocks；保留 ChartSpec 兼容；见 ADR-003、`24`；LLM 见 14 |
| 部署 | 11.12 以本机 Windows 工作站作为服务器，局域网 `http://10.62.172.85:5173/`；微信小程序实测；Compose/Nginx/Dockerfile/CI 保留为云方案 |
| 下一步 | B-003 DOING：MP16 登录入口、页面地图 v2、小程序页面优化、Web/MP 视觉与按钮秩序 |
| 最大风险 | 小程序登录入口缺失、页面地图过期、双端视觉未对齐；微信真机/真实数据待验证 |

## 0.1 本轮上下文保护快照（2026-11-10）

- 分支：`feat/b002-demo-v0`；B04 代码 `29dfe61`，B04 文档 `e3a8a45`，上下文收口 `1ae4438`。
- 已完成：B00 脚手架、B01 模型/迁移、B02 合成种子、B04 只读查询 API。
- 验证：`pytest` 36 passed；`alembic upgrade/downgrade/check` 通过；OpenAPI 14 paths。
- 未开始：C01/C02 认证/申请/后台、D01~D05 小程序、E01~E03 AI/组件、F 部署联调。
- 新会话先读：本文件、`04-tasks.md`、`21`~`25`、`product/06`、`product/07`。
- 验证命令：`cd services/api && python -m pytest -q`；`python -m alembic -c alembic.ini upgrade head`；`python scripts/seed_demo.py --check`。
- 已知边界：OpenAPI 仅 B04 查询端点；认证/AI/管理端待补；尚未做云服务器部署（当前切本机服务器）。

## 0.2 六步推进快照（2026-11-10）

| Step | 状态 | 结果 |
|---|---|---|
| 1 契约收口 | DONE | `period_year`/`root_code`、`JD-Z-01/02`、分页 20/100、category/value_type/quality_status、dashboard coverage；OpenAPI 重新生成 |
| 2 认证/后台 | DONE | 16 个认证/申请/审批/用户/审计/导入端点；migration 0002；80 tests；Web 后台 build 通过 |
| 3 小程序 | DONE（DevTools 待验证） | 10 页 + 3 组件 + ChartSpec Canvas 2D；`tsc --noEmit` 与 JSON/WXML 校验通过 |
| 4 AI/导出 | DONE | `/ai/chat` + AnswerBlocks + 10 工具 + 引用；PNG/PDF/XLSX/CSV 导出；migration 0003 |
| 5 种子/部署 | DONE（本机） | 数据库已播种 227/15/1608/42；SQLite FK/WAL；本机 API/Web 监听 `0.0.0.0`；Compose/Nginx 保留为云方案 |
| 6 文档收口 | DONE | 00/01/03/04/05/06/07/09/11/12/15/18/20/21/22/23/24/25/批次记录与 OpenAPI 已同步 |

- 当前测试：后端 119 passed；Web `pnpm build` 通过；小程序 `tsc --noEmit` 通过；`check-links` 49 个 Markdown 通过；`check-no-emoji` 57 个 Markdown 通过（已排除 node_modules）。
- 导出 smoke：CSV 194B、XLSX 6090B、PNG 333872B、PDF 67744B、AI 答案 XLSX 6829B；下载均 200。
- 真实 DeepSeek Key 已联调（本地 `.env`，不入 Git）：`model=deepseek-chat`、`degraded=false`；云路镇常住人口 31038、玉湖镇画像均返回真实数据与引用。
- 已确认边界：`曲溪街道 + 常住人口` 在合成种子中为 missing，AI 返回 no_data；演示可用 `云路镇 + 常住人口`（31038）替代。

## 0.3 B-003 交接快照（2026-11-10）

**批次**：`B-003 小程序登录与双端视觉对齐`（DOING），详情见 [B-003-ui-auth-alignment.md](08-batch-log/B-003-ui-auth-alignment.md)。

**必须先修**：

- 小程序没有账号登录页/入口；申请已批准用户、电脑端批量建号用户无法登录。
- MP08“我的”只有退出，没有“登录/切换账号”；MP14 approved 没有“去登录”。
- 首次登录改密未闭环：后端 `must_change_password`/`POST /auth/change-password` 已有，前端没有入口。
- `page-map.html` 是 v1（18 页），不含 MP09–MP16、AD10–AD13、登录/申请/导出/管理真实页面；关系/数据流/事件/相对位置不足。
- MP 与 Web 的颜色/字号/间距/按钮层级未统一；部分页面按钮排列缺少主次。

**任务顺序**：

1. `MP-009` MP16 登录页 + `MP-010` 入口/申请通过引导 + `MP-011` 首改密/401/禁用态。
2. `UI-001` 页面地图 v2（29 页；关系/数据流/触发事件/相对位置；筛选/详情/缩放/导出）。
3. `UI-004` 双端按钮规范 → `UI-002` 小程序 11 页优化 + `UI-003` Web/MP 视觉对齐。
4. `QA-005` 双端走查与截图；`DOC-033` 批次/交接同步。

**验收**：MP16 两类账号登录成功；页面地图 29 页且能走通“登录→首页→指标→导出→申请”；双端 token/按钮一致；119+ tests、Web build、MP typecheck、页面地图冒烟通过。

**本机服务器**：API `0.0.0.0:8000`，Web `0.0.0.0:5173`；局域网 `http://10.62.172.85:5173/`；演示账号 `admin / Admin#2026demo`；测试 Key/JWT Secret 只在本地 `.env`。

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

然后给我一个 3–5 步计划。除 trivial 修改外，非简单任务必须先拆工作包，再按 category/skills 委派 subagent；主 agent 负责审查 diff、集成、复跑验证与留痕，不能直接包办，子代理自述不能作为完成依据。上下文接近 85% 时先更新本文件/批次记录/任务板，再决定是否继续。

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
- 不要跳过规划直接写代码；除 trivial 修改外，非简单任务必须先拆工作包并委派 subagent，主 agent 审查、集成并复跑验收，不能直接包办。
- 不要在上下文接近 85% 后继续开新任务；先写交接、批次记录与未完成项，再收尾或提交。
- 不要把 `.env`、API Key、数据库密码、JWT Secret、微信 AppSecret 写入仓库；密钥只放本地环境变量或 gitignored `.env`。
- 不要在工程文档或 README 中使用 emoji。
