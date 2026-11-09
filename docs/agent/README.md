# Agent 加载指南

> owner: 项目开发者 · last_updated: 2026-11-06 · read_when: 第一次让 agent 接手本仓库任务

这份文档解决四件事：**先读什么、以什么为准、改完同步什么、什么时候停**。

## 1. 默认加载顺序

任何新会话，先读这三份（通常 < 250 行）：

1. [00-context.md](00-context.md) — 项目是什么、现在到哪、下一步
2. [04-tasks.md](04-tasks.md) — 当前批次任务与验收标准
3. [05-architecture.md](05-architecture.md) 的「2 技术栈」「6 数据模型」「7 API v0」「8 Agent 设计」四节

然后按任务类型追加：

| 任务类型 | 追加读 | 不要读 |
|---|---|---|
| 后端接口/数据库 | [06-file-tree.md](06-file-tree.md)、[07-workflow.md](07-workflow.md)、[09-risks.md](09-risks.md) 的数据/安全节 | 小程序页面细节 |
| Web 后台 | [06-file-tree.md](06-file-tree.md)、[product/03-page-specs.md](../product/03-page-specs.md)、[product/02-ia-and-flows.md](../product/02-ia-and-flows.md) | LLM 内部实现 |
| 原生微信小程序 | [06-file-tree.md](06-file-tree.md)、[product/02-ia-and-flows.md](../product/02-ia-and-flows.md)、[product/04-data-catalog.md](../product/04-data-catalog.md)、[13-tech-stack-review.md](13-tech-stack-review.md) | 数据库迁移细节 |
| AI/Agent | [05-architecture.md](05-architecture.md) 的 Agent 节、[ADR-003](../adr/ADR-003-agent-architecture.md)、[09-risks.md](09-risks.md) 的 AI 节 | 后台 CRUD 细节 |
| 部署/合规 | [07-workflow.md](07-workflow.md)、[ADR-004](../adr/ADR-004-deployment-and-compliance.md)、[09-risks.md](09-risks.md) | 产品交互细节 |
| 修 bug | [09-risks.md](09-risks.md) 对应条目、[05-architecture.md](05-architecture.md)、相关代码 | 全量产品文档 |
| 接续上一批 | [08-batch-log/](08-batch-log/) 最新一篇 + [11-handoff.md](11-handoff.md) | 全量重读 |
| 需求澄清 | [01-project.md](01-project.md)、[12-open-questions.md](12-open-questions.md) | 代码细节 |
| 页面/流程设计 | [18-workflows.md](18-workflows.md)、[05-page-structure.md](../product/05-page-structure.md)、[ue/page-map.html](../product/ue/page-map.html) | 数据库迁移细节 |
| 代码冲刺/委派 | [20-b002-delegation-plan.md](20-b002-delegation-plan.md)、[07-workflow.md](07-workflow.md) | 全量历史文档 |

## 2. 事实来源优先级

1. **代码与 OpenAPI 实际输出**：实现细节的最终事实。
2. **`05-architecture.md`**：技术栈、数据模型、API、Agent 契约；改接口先改这里。
3. **`docs/product/01-prd-lite.md` + `02-ia-and-flows.md`**：范围、交互、验收。
4. **`01-project.md` / `02-goals.md`**：背景、边界、目标。
5. **`03-roadmap.md` / `04-tasks.md`**：进度与任务。
6. **`Resource/` 原始材料**：背景参考，不是准则；且不得复制进仓库。

冲突处理：**范围/交互 → 产品文档；API/数据/技术 → 05**；跨域变更先记 ADR，再改代码。

## 3. 任务 ID 约定

| 前缀 | 范围 |
|---|---|
| `DOC-` | 文档、流程、模板 |
| `DATA-` | 数据模型、导入、数据治理 |
| `BE-` | 后端接口、服务、数据库 |
| `FE-` | Web 后台 |
| `MP-` | 原生微信小程序 |
| `AI-` | LLM/Agent/Prompt/图表生成 |
| `OPS-` | 部署、CI、环境、监控 |
| `PKG-` | packages/contracts、chart-spec、生成链路 |
| `QA-` | 测试、验收、可用性 |
| `YX-` | 粤政易/等保/信创对接 |
| `SH-` | 跨模块/项目管理 |
| `WP-` | 子代理工作包（如 WP-BE1、WP-DATA1） |

引用任务写完整 ID，例如“完成 DATA-003 后开始 BE-005”。

## 3.1 任务执行方式

- 非简单任务先写工作包，再委派 subagent；主 agent 负责集成与复跑验证。
- 子代理不得直接 commit/push；共享文件由主 agent 统一修改。
- 工程文档不使用 emoji；README 保持正式。
- 详细模板见 `20-b002-delegation-plan.md`。

## 4. 状态图例

`TODO` 未开始 · `DOING` 进行中 · `DONE` 已完成 · `BLOCKED` 被阻塞 · `DEFERRED` 明确延期/不做 · `PROPOSED` 待确认 · `ACCEPTED` 已确认 · `SUPERSEDED` 被取代。

## 5. 写代码前的自检

- [ ] 这个任务在 `04-tasks.md` 里有 ID、优先级、验收标准吗？
- [ ] 接口在 `05-architecture.md` 里有定义吗？没有就先加，或先记 ADR。
- [ ] 文件放在 `06-file-tree.md` 规定的位置了吗？
- [ ] 是否碰到 `09-risks.md` 里的高风险项？碰到就先读缓解措施。
- [ ] 是否要改 `Resource/`？**不允许**。
- [ ] 是否要把密钥写进代码/文档？**不允许**。
- [ ] 是否扩大了 P0 范围？**不允许**。
- [ ] 是否会新增顶层目录？**先改文档并说明理由**。

## 6. 改完要同步什么

| 你改了什么 | 必须同步 |
|---|---|
| API 路径/字段/错误码 | `05-architecture.md`、`contracts/openapi.json`、`packages/contracts` |
| 数据表/字段/迁移 | `05-architecture.md` 数据模型、`06-file-tree.md`（如新增目录） |
| 新增页面/组件目录 | `06-file-tree.md`、`docs/product/03-page-specs.md` |
| 任务完成/阻塞 | `04-tasks.md`、最新批次记录 |
| 范围变化 | `01-project.md`、`02-goals.md`、ADR |
| 不可逆技术决策 | `docs/adr/` 新增 ADR |
| 新的高风险 | `09-risks.md` |
| 当前快照变化 | `11-handoff.md`、`00-context.md` |

## 7. 上下文预算

- 单次任务优先读 **3 份以内**文档；不要一次性把 `docs/` 全读。
- 需要历史决策读 `docs/adr/`，不要翻聊天记录。
- 需要原始材料时读 [10-resources.md](10-resources.md) 的摘要；摘要不够再打开本地 `Resource/`。
- 长文档（`05-architecture.md`、`04-data-catalog.md`）按标题跳读。
- 核心架构/数据目录可按节读到 700 行；调研/报告可到 400 行；其他文档超过 300 行时，拆成“速览 + 细节”两份。

## 8. 批次记录规则

- 每批次开始前复制 [08-batch-log/B-000-template.md](08-batch-log/B-000-template.md) 为 `B-xxx-<slug>.md`。
- 记录**目标、范围、非目标、动作、决策、验证证据、文档同步、下一步**。
- 不记录原始聊天、不粘贴大段工具输出；只保留可复核的命令、文件、结果。
- 批次结束后更新 [08-batch-log/README.md](08-batch-log/README.md) 索引与 [11-handoff.md](11-handoff.md)。

## 9. 当前快照

不要在本文件维护进度；以 [11-handoff.md](11-handoff.md) 的「当前快照」为准，避免两处不一致。
