# AGENTS.md · i揭东 Agent 入口

> 任何 agent 进入本仓库，先读本文件，再按 `docs/agent/README.md` 的路由读取最少必要文档。
> 本文件是**约束**，不是项目介绍；项目介绍看 `docs/agent/00-context.md`。

## 1. 当前阶段

- 阶段：**M0.5 11.12 初步 demo**（2026-11-06 起）
- 当前状态：文档/决策/三类工作流/费用调研/目录骨架/页面结构地图已完成；业务代码尚未开始
- 当前批次：`B-002 11.12 demo 冲刺`（文档/方案已完成，等待确认后开始代码；见 `docs/agent/15-demo-plan-1112.md`）
- 已确认：公职人员；原生微信小程序；粤政易等程序搭建完再接；数据来源 Excel/接口/手工；DeepSeek API；11.12 前 demo+文档+成本
- 当前头号风险：6 天截止过紧、原生小程序图表、真实数据/Key/AppID 未到

## 2. 必读顺序

任何新会话：

1. `docs/agent/00-context.md` — 30 秒了解项目全貌
2. `docs/agent/04-tasks.md` — 当前批次与可领取任务
3. `docs/agent/05-architecture.md` 的「技术栈」「数据模型」「API v0」「Agent 设计」四节

然后按任务追加：

| 任务 | 追加读 | 不要读 |
|---|---|---|
| 后端/数据 | `06-file-tree.md`、`09-risks.md` 的数据与安全部分 | 小程序页面细节 |
| Web 后台 | `06-file-tree.md`、`docs/product/03-page-specs.md` | LLM 内部实现 |
| 原生小程序 | `06-file-tree.md`、`docs/product/02-ia-and-flows.md`、`13-tech-stack-review.md` | 数据库迁移细节 |
| AI/Agent | `05-architecture.md` 的 Agent 节、`ADR-003`、`09-risks.md` 的 AI 部分 | 后台 CRUD 细节 |
| 部署/合规 | `07-workflow.md`、`ADR-004`、`09-risks.md` | 产品交互细节 |
| 11.12 冲刺 | `15-demo-plan-1112.md`、`16-cost-estimate.md`、`17-outreach-copy.md` | 全量历史文档 |
| 页面/交互设计 | `docs/product/05-page-structure.md`、`docs/product/ue/page-map.html`、`18-workflows.md` | 数据库迁移细节 |
| 预算/资源 | `19-cost-research.md`、`16-cost-estimate.md` | 页面视觉细节 |
| 接续上一批 | `08-batch-log/` 最新一篇 + `11-handoff.md` | 全量重读 |

## 3. 硬规则（违反即停）

1. **不修改 `Resource/`**。它只读、且被 gitignore。
2. **不提交密钥**：`.env`、API Key、数据库密码、JWT Secret、微信 AppSecret 一律不进仓库。
3. **不凭记忆写接口**：以 `05-architecture.md` / `contracts/openapi.json` 为准；没有就先改文档。
4. **不直接写业务代码**：先有任务 ID、验收标准、批次记录；再实现。
5. **不让 LLM 直连数据库或生成任意 SQL**：只允许调用受控只读工具。
6. **不扩大范围**：P0/P1/P2 以 `01-project.md` 为准；不做模型训练、不做完整 BI、不做未被要求的公共开放。
7. **不删除失败测试**，不用 `as any` / `@ts-ignore` / `# type: ignore` 掩盖问题。
8. **不新建顶层目录**：按 `06-file-tree.md` 放置；确需新增，先改文档并说明理由。
9. **不跳过验证**：没有命令输出/截图/测试结果，不得标记 DONE。
10. **每批次必须留痕**：更新 `08-batch-log/`、`04-tasks.md`、`11-handoff.md`。

## 4. 批次工作流（单人 + agent）

```text
读上下文 → 选任务 → 写批次计划 → 实现 → 自测 → 更新文档 → 记录批次 → 交接
```

- 一个批次 0.5–2 天，必须有明确目标、范围、非目标、验收标准。
- 批次 ID：`B-001`、`B-002`……；记录模板见 `docs/agent/08-batch-log/B-000-template.md`。
- 代码改动前后都要更新文档：API/数据/目录变化先改 `05/06`，再改代码。
- 完成后把状态写回 `04-tasks.md`，并把“当前快照”更新到 `11-handoff.md`。

## 5. 事实来源优先级

1. 代码与 OpenAPI 实际输出（实现细节）
2. `docs/agent/05-architecture.md`（技术栈/数据/API/Agent 契约）
3. `docs/product/01-prd-lite.md` + `02-ia-and-flows.md`（范围/交互/验收）
4. `docs/agent/01-project.md` + `02-goals.md`（背景/目标/边界）
5. `docs/agent/03-roadmap.md` + `04-tasks.md`（进度/任务）
6. `Resource/` 原始材料（背景参考，不是准则）

冲突时：范围/交互以产品文档为准；API/数据/技术以 05 为准；两者都受影响时先记 ADR，再改代码。

## 6. 文件放置速查

| 内容 | 位置 |
|---|---|
| Agent 工程上下文 | `docs/agent/` |
| 产品/交互/页面规范/数据目录 | `docs/product/` |
| 架构决策 | `docs/adr/` |
| Web 后台 | `apps/admin/` |
| 原生微信小程序 | `apps/mp/` |
| 后端 | `services/api/` |
| OpenAPI 契约 | `contracts/` |
| 共享 TS 类型 | `packages/contracts/` |
| 图表 spec 渲染 | `packages/chart-spec/` |
| 部署 | `deploy/` |
| 本地资料/学习/工具 | `Resource/`、`learning/`、`tools/`（均 gitignore） |

## 7. 当前批次交接

```text
你是 i揭东项目的开发 agent。
先读：AGENTS.md → docs/agent/00-context.md → docs/agent/04-tasks.md → docs/agent/05-architecture.md 的相关节。
不要立刻写代码。先用 5 行复述：项目一句话、当前阶段、任务 ID/验收标准、关键约束、最大风险。
然后给出 3–5 步计划，等我确认后再动手。
当前任务：<任务 ID + 一句话>
范围：<只改哪些目录/文件>
不做：<明确排除项>
验收：<可验证标准>
```
