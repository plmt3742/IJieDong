---
owner: 项目开发者
last_updated: 2026-11-10
status: active
read_when: 每次新会话的第一份文档；需要 30 秒了解项目全貌
---

# 00 · 项目速览

## 一句话

把揭东区、镇街、村居的政府数据数字化存储，做成**可查、可看、可问**的移动数据门户：浏览指标、看图表、用自然语言问数据并生成图表。

仓库：https://github.com/plmt3742/IJieDong

## 产品闭环

```text
数据导入/校验（Excel/手工）
        ↓
区域 + 指标 + 数据值（可审计）
        ↓
微信小程序浏览：区域 → 指标 → 图表
        ↓
AI 问答：自然语言 → 受控工具查询 → 答案 + 图表 + 数据依据
        ↓
管理后台：导入、修订、审计、问答记录
```

## 当前阶段

**M0：理解与骨架 → M0.5：11.12 初步 demo**（2026-11-06 起）

- 已完成：原始材料分析、数据模板拆解、技术栈/数据模型/Agent/部署决策、agent 文档体系、批次记录模板、文档内链检查。
- 已完成（双线工程）：① 有来源的费用调研（`19-cost-research.md`）；② 用户/开发/系统三类工作流（`18-workflows.md`）；③ 目录骨架与 `.gitkeep`；④ 18 页低保真线框、线框总览（`wireframes.html`）与可缩放/可点击页面地图（`page-map.html`）；⑤ B-002 子代理委派计划（`20-b002-delegation-plan.md`）。
- 已完成（2026-11-10 契约冻结）：数据/API、认证/申请、页面设计 v2、AI/AnswerBlocks、组件库、导出共 7 份契约草案（`21`~`25`、`product/06`、`product/07`）。
- 已确认：公职人员使用；原生微信小程序；后续接粤政易；数据来源 Excel/API/手工；DeepSeek API；11.12 可运行 Demo v0，小服务器 + 小程序实测，Web 后台可视化；游客不可导出，导出 PNG/PDF/XLSX/CSV 且不设默认。
- 未开始：可运行代码、数据库、API、页面。
- Git：已推送 `origin/main`；最新提交见 `git log`；工作区有未提交文档改动（决策/契约草案）。
- 当前批次：`B-002 11.12 demo 冲刺`（决策/契约已完成；下一步按原子任务进入数据底座与三端实现）。

## 技术栈（已确认方向，B-002 验证）

| 层 | 选型 |
|---|---|
| 小程序 | **原生微信小程序 + TypeScript + TDesign Miniprogram + echarts-for-weixin** |
| Web 后台 | Vue 3 + Vite + TypeScript + Element Plus + ECharts |
| 后端 | Python 3.13 + FastAPI + SQLAlchemy 2.0 + Alembic |
| 数据库 | **SQLite（11.12 demo）/ PostgreSQL 16（生产）** |
| LLM/Agent | **DeepSeek API（OpenAI 兼容）** + 工具调用；可切 Qwen/GLM/vLLM/Ollama |
| 图表 | ECharts 5 + 平台无关 `ChartSpec` |
| 部署 | 11.12 本地进程；生产 Docker Compose + Nginx；预留 ARM64/政务外网 |

详见 [05-architecture.md](05-architecture.md) 与 [ADR-001](../adr/ADR-001-tech-stack.md)。

## 已从材料确认的事实

1. **数据模板**：15 个指标、3 个区域层级（揭东区 / 15 个镇街 / 211 个村居）、227 个区域、数据期仅 2025、数据值全部为空。
2. **指标类型**：2 个文本指标（地区简介、地区特色）+ 13 个数值指标；单位含平方公里、个、人、亩、亿元。
3. **粤政易**：支持 WEB 网页、移动 H5、微信小程序；平台仅处理非密、非敏感信息；工作台入口、单点登录、统一待办等为可选公共能力。
4. **合规**：需功能测试报告、安全测试报告、等保（指引中出现二级/三级两种表述）、信创符合性测试、密码评估等；暂无粤政易测试账号，需向省申请。
5. **网络**：应用可部署在互联网、单位局域网或政务外网；只有政务外网部署才能对接粤政易单点登录等公共能力。

详细摘要见 [10-resources.md](10-resources.md)，数据目录见 [product/04-data-catalog.md](../product/04-data-catalog.md)。

## 已确认/建议的决策

| ID | 决策 | 状态 |
|---|---|---|
| Q-01 | 用户对象为**公职人员**；微信小程序后续接入粤政易工作台 | 已确认 |
| Q-02 | 数据来源支持 **Excel 导入 / 接口 / 手工录入**；更新频率由使用方决定，每次导入更新一批 | 已确认 |
| Q-03 | 当前以现有 15 指标/2025 年为准；后续增加数据类型，可再对接 | 已确认（边界） |
| Q-04 | 初期接入 **DeepSeek API**；生产是否私有化待数据密级确认 | 已确认（方向） |
| Q-05 | 粤政易**等程序搭建完再接入** | 已确认 |
| Q-06 | **11.12 前**完成初步 demo + 技术文档 + 开发必要支出评估 | 已确认 |
| ADR-001 | Vue3 + FastAPI + SQLite/PostgreSQL + ECharts（移动端见 ADR-005） | Accepted |
| ADR-002 | 区域/指标/数据值规范化模型（非宽表） | Proposed |
| ADR-003 | Agent 只调用受控只读工具；LLM 不生成 SQL/JS；图表用 ChartSpec | Proposed |
| ADR-004 | 11.12 本地演示；粤政易/等保/信创后置；架构预留 | Proposed |
| ADR-005 | 移动端改用**原生微信小程序** | Accepted |

## 头号风险

1. **数据未到位**：xls 是空白模板，真实数据、更新频率、责任人未确认。
2. **质量优先下的范围控制**：11.12 是 Demo v0，时间不是压缩质量的理由；但未来类型、最终视觉、合规不能塞进同一批，必须按原子任务与验收推进。
3. **粤政易/等保/信创周期长**：外部审批、测评、网络策略不可控，不能按普通 Web 项目排期。
4. **单人开发 + 范围过大**：数据平台 + 可视化 + AI + 小程序 + 合规，必须分阶段。
5. **LLM 数据安全与准确性**：敏感数据不能出网、答案必须可追溯、图表不能由模型随意生成。

详见 [09-risks.md](09-risks.md)。

## 仍需确认的问题（不阻塞 11.12 demo）

1. 玉滘镇/玉窖镇对外统一用哪个写法？
2. 真实数据样例、更新频率、后续指标清单、历史年份。
3. DeepSeek 公有云是否允许？数据是否非密/非敏感？
4. 粤政易部署网络（互联网/政务外网）、等保二级/三级、测试账号。
5. 11.12 验收人/标准；是否需要公网 demo；AppID/域名/服务器谁提供。

完整列表与建议见 [12-open-questions.md](12-open-questions.md)；对外话术见 [17-outreach-copy.md](17-outreach-copy.md)。

## 下一步（11.12 冲刺）

1. 按原子任务依赖推进：B01 数据模型/迁移 → B02 合成种子 → B04 查询 API；C/D/E 在契约冻结后并行。
2. 按 [21-technical-architecture-v2.md](21-technical-architecture-v2.md) 的 Demo v0 子集和 [15-demo-plan-1112.md](15-demo-plan-1112.md) §11 验收。
3. 页面设计以 [product/06-page-design-v2.md](../product/06-page-design-v2.md) 为准；旧结构图见 [05-page-structure.md](../product/05-page-structure.md) / [ue/page-map.html](../product/ue/page-map.html)；数据流见 [18-workflows.md](18-workflows.md)。
4. 11.12 前产出可运行 Demo v0、技术文档、[16-cost-estimate.md](16-cost-estimate.md)、[17-outreach-copy.md](17-outreach-copy.md)。
5. 11.12 后再补数据治理、未来数据类型、视觉风格、粤政易/等保/信创。

## 文档入口

- Agent 加载策略：[README.md](README.md)
- 项目定义：[01-project.md](01-project.md)
- 目标与验收：[02-goals.md](02-goals.md)
- 路线与批次：[03-roadmap.md](03-roadmap.md)
- 任务清单：[04-tasks.md](04-tasks.md)
- 架构契约：[05-architecture.md](05-architecture.md)
- 文件树：[06-file-tree.md](06-file-tree.md)
- 批次记录：[08-batch-log/](08-batch-log/)
- 三类工作流：[18-workflows.md](18-workflows.md)
- 费用调研：[19-cost-research.md](19-cost-research.md)
- B-002 委派计划：[20-b002-delegation-plan.md](20-b002-delegation-plan.md)
- 契约 v2：[21 技术架构](21-technical-architecture-v2.md)、[22 数据接入](22-data-integration-spec.md)、[23 认证/申请](23-auth-and-application-spec.md)、[24 AI](24-ai-and-component-spec.md)、[25 导出](25-export-spec.md)
- 页面设计 v2：[product/06-page-design-v2.md](../product/06-page-design-v2.md)
- 组件库规范：[product/07-component-library-spec.md](../product/07-component-library-spec.md)
- 页面结构（旧）：[product/05-page-structure.md](../product/05-page-structure.md) / [ue/page-map.html](../product/ue/page-map.html)
- 交接快照：[11-handoff.md](11-handoff.md)
