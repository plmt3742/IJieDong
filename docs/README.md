# 项目文档总索引

本仓库文档分三层，目标不是“写全”，而是让 agent 在最少上下文内做对事。

| 层 | 目录 | 用途 | 事实强度 |
|---|---|---|---|
| Agent 工程上下文 | `docs/agent/` | 项目背景、目标、进度、任务、架构、文件树、工作流、风险、交接、批次记录 | 强约束 |
| 产品设计 | `docs/product/` | PRD、信息架构、页面规范、数据目录 | 范围/交互依据 |
| 架构决策 | `docs/adr/` | 不可逆或跨模块决策的记录 | 决策依据 |

## 从哪里开始

| 场景 | 先读 |
|---|---|
| 第一次进入项目 | [agent/00-context.md](agent/00-context.md) |
| 当前要做什么 | [agent/03-roadmap.md](agent/03-roadmap.md) + [agent/04-tasks.md](agent/04-tasks.md) |
| 写代码前 | [agent/05-architecture.md](agent/05-architecture.md) + [agent/06-file-tree.md](agent/06-file-tree.md) |
| 做产品/页面 | [product/01-prd-lite.md](product/01-prd-lite.md) + [product/02-ia-and-flows.md](product/02-ia-and-flows.md) |
| 查数据指标 | [product/04-data-catalog.md](product/04-data-catalog.md) |
| 看页面结构/交互地图 | [product/05-page-structure.md](product/05-page-structure.md) + [product/ue/page-map.html](product/ue/page-map.html) |
| 看三类工作流 | [agent/18-workflows.md](agent/18-workflows.md) |
| 查费用调研 | [agent/19-cost-research.md](agent/19-cost-research.md) |
| 查风险/合规 | [agent/09-risks.md](agent/09-risks.md) + [adr/ADR-004-deployment-and-compliance.md](adr/ADR-004-deployment-and-compliance.md) |
| 查原始资料摘要 | [agent/10-resources.md](agent/10-resources.md) |
| 切换会话/交接 | [agent/11-handoff.md](agent/11-handoff.md) |
| 查未确认需求 | [agent/12-open-questions.md](agent/12-open-questions.md) |
| 11.12 冲刺 | [agent/15-demo-plan-1112.md](agent/15-demo-plan-1112.md) + [agent/20-b002-delegation-plan.md](agent/20-b002-delegation-plan.md) |
| 向对方提问 | [agent/17-outreach-copy.md](agent/17-outreach-copy.md) |
| 看每批次 agent 做了什么 | [agent/08-batch-log/](agent/08-batch-log/) |

## 文档清单

### Agent 上下文

| 文件 | 内容 | 何时读 |
|---|---|---|
| [agent/README.md](agent/README.md) | agent 加载策略、事实源、任务 ID、同步规则、上下文预算 | 第一次让 agent 接手 |
| [agent/00-context.md](agent/00-context.md) | 一页纸：项目、阶段、栈、状态、风险、下一步 | 每次新会话 |
| [agent/01-project.md](agent/01-project.md) | 背景、用户、价值、范围、非目标、约束、干系人、开发体量 | 判断“该不该做” |
| [agent/02-goals.md](agent/02-goals.md) | 产品/技术/交付目标、验收标准、指标、DoD | 判断“做到什么程度算完成” |
| [agent/03-roadmap.md](agent/03-roadmap.md) | 里程碑、批次计划、当前进度、关键路径 | 每次开工/收工 |
| [agent/04-tasks.md](agent/04-tasks.md) | 任务清单：ID、优先级、依赖、验收、状态 | 领取任务/同步进度 |
| [agent/05-architecture.md](agent/05-architecture.md) | 架构、技术栈、数据模型、API v0、Agent 设计、安全 | 写代码前 |
| [agent/06-file-tree.md](agent/06-file-tree.md) | 目标文件树、目录职责、命名、放置决策树 | 新建文件/目录前 |
| [agent/07-workflow.md](agent/07-workflow.md) | 单人+agent 批次工作流、Git、DoD、文档同步 | 第一次提交前 |
| [agent/08-batch-log/README.md](agent/08-batch-log/README.md) | 批次记录规则、模板、索引 | 每批次开始/结束 |
| [agent/09-risks.md](agent/09-risks.md) | 风险登记册、实现注意事项、演示兜底 | 每次批次复盘 |
| [agent/10-resources.md](agent/10-resources.md) | 本地资料摘要、外部链接、术语表 | 查资料 |
| [agent/11-handoff.md](agent/11-handoff.md) | 当前快照、启动提示词、角色模板、交接检查 | 切换会话 |
| [agent/12-open-questions.md](agent/12-open-questions.md) | 待确认需求、影响、建议、阻塞级别 | 需求澄清/评审 |
| [agent/13-tech-stack-review.md](agent/13-tech-stack-review.md) | 原生小程序 + 后台/后端/数据库/LLM 技术栈复审 | 选型复核 |
| [agent/14-llm-deployment.md](agent/14-llm-deployment.md) | 公有云/政务云/私有化 LLM 方案、成本、安全、DeepSeek | LLM 决策/预算 |
| [agent/15-demo-plan-1112.md](agent/15-demo-plan-1112.md) | 11.12 demo 范围、6 天排期、验收、砍范围顺序 | 11.12 冲刺 |
| [agent/16-cost-estimate.md](agent/16-cost-estimate.md) | demo/生产/合规/人力成本速查 | 预算/资源申请 |
| [agent/17-outreach-copy.md](agent/17-outreach-copy.md) | 可直接发给需求方/政数局的通俗问题 | 对外对接 |
| [agent/18-workflows.md](agent/18-workflows.md) | 用户/开发/系统三类工作流（Mermaid） | 设计/开发前 |
| [agent/19-cost-research.md](agent/19-cost-research.md) | 有来源的云资源/LLM/合规费用调研 | 预算/报价 |
| [agent/20-b002-delegation-plan.md](agent/20-b002-delegation-plan.md) | B-002 子代理工作包、文件归属、验收、提示词模板 | 代码冲刺/交接 |

### 产品设计

| 文件 | 内容 | 状态 |
|---|---|---|
| [product/README.md](product/README.md) | 产品文档索引与状态 | 有效 |
| [product/01-prd-lite.md](product/01-prd-lite.md) | 一页纸 PRD：问题、用户、闭环、P0/P1/P2、指标 | 初稿 |
| [product/02-ia-and-flows.md](product/02-ia-and-flows.md) | 信息架构、页面清单、3 条核心流程、AI 状态机 | 初稿 |
| [product/03-page-specs.md](product/03-page-specs.md) | 页面规范模板与页面清单 | 模板 |
| [product/04-data-catalog.md](product/04-data-catalog.md) | 数据模板分析：区域层级、15 个指标、数据质量、导入规则 | 初稿 |
| [product/05-page-structure.md](product/05-page-structure.md) | 页面清单、跳转/数据传递、页面详情 | 初稿 |
| [product/ue/page-map.html](product/ue/page-map.html) | 可缩放/可点击的页面结构地图（离线单文件） | 可验证 |
| [product/ue/wireframes.html](product/ue/wireframes.html) | 18 页低保真线框总览（灰度、无品牌风格） | 可验证 |

### 架构决策

| 文件 | 内容 | 状态 |
|---|---|---|
| [adr/README.md](adr/README.md) | ADR 索引与写法 | 有效 |
| [adr/ADR-000-template.md](adr/ADR-000-template.md) | ADR 模板 | 模板 |
| [adr/ADR-001-tech-stack.md](adr/ADR-001-tech-stack.md) | 技术栈：Vue3 + FastAPI + SQLite/PostgreSQL + ECharts（移动端见 ADR-005） | Accepted |
| [adr/ADR-002-data-model.md](adr/ADR-002-data-model.md) | 区域/指标/数据值规范化模型 | Proposed |
| [adr/ADR-003-agent-architecture.md](adr/ADR-003-agent-architecture.md) | 工具调用 Agent + ChartSpec，不生成 SQL/JS | Proposed |
| [adr/ADR-004-deployment-and-compliance.md](adr/ADR-004-deployment-and-compliance.md) | 部署、粤政易、等保/信创的分阶段策略 | Proposed |
| [adr/ADR-005-native-wechat-miniprogram.md](adr/ADR-005-native-wechat-miniprogram.md) | 移动端改用原生微信小程序 | Accepted |

## 状态图例

| 标记 | 含义 |
|---|---|
| `TODO` | 未开始 |
| `DOING` | 进行中 |
| `DONE` | 已完成 |
| `BLOCKED` | 被阻塞，需外部输入 |
| `DEFERRED` | 明确延期/不做，附原因 |
| `PROPOSED` | 待确认 |
| `ACCEPTED` | 已确认 |
| `SUPERSEDED` | 被新决策取代 |

## 维护规则

1. **小文件优先**：单篇尽量 ≤ 300 行；核心架构/数据目录可到 700 行；调研/报告可到 400 行；都必须按节读取，不整篇塞上下文。
2. **单一事实来源**：任务状态以 `04-tasks.md` 为准；API 以 `05-architecture.md` + OpenAPI 为准；范围以 `01-project.md` 为准。
3. **先改文档再改代码**：API、数据模型、目录结构变化必须先改文档。
4. **每批次必须更新**：`04-tasks.md`、`08-batch-log/` 最新一篇、`11-handoff.md`。
5. **决策留痕**：不可逆或跨模块决策写 ADR，不要只留在聊天记录。
6. **不复制原文**：`Resource/` 只做摘要，原文留在本地。
7. **不写密钥**：文档、示例、日志中都不出现真实密钥。
8. **不使用 emoji**：工程文档与 README 一律使用正式文字；`scripts/check-no-emoji.py` 校验。
9. **先规划再委派**：非简单任务先写工作包，再委派 subagent；主 agent 负责集成与复跑验证。

## 变更记录

| 日期 | 变更 |
|---|---|
| 2026-11-06 | 初始化三层文档体系；新增 agent 批次记录、数据目录、开放问题、4 份 ADR |
| 2026-11-06 | 确认公职人员/原生小程序/粤政易后置/DeepSeek API/11.12 截止；新增技术栈复审、LLM 方案、11.12 计划、成本、对接文案、ADR-005 |
