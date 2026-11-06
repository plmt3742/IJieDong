# ADR 索引

ADR（Architecture Decision Record）= 架构决策记录。记录**不可逆或跨模块**的决定，避免“为什么当时这么定”只留在聊天记录里。

## 什么时候写

- 技术栈/框架/数据库/部署方式选型或变更。
- API 风格、认证方式、数据模型的关键取舍。
- 范围裁剪（如“不做地图/不做 SSO”）。
- 引入新基础设施（队列、对象存储、向量库等）。
- 任何“以后再改成本很高”的决定。

不需要写：变量命名、样式微调、单个 bug、日常任务拆分。

## 状态

| 状态 | 含义 |
|---|---|
| `Proposed` | 已提出，待确认/验证 |
| `Accepted` | 已确认，按此执行 |
| `Superseded` | 被新 ADR 取代（注明编号） |
| `Deprecated` | 不再使用，保留记录 |
| `Rejected` | 评估后不采用（保留原因） |

## 命名

`ADR-<三位编号>-<短横线标题>.md`。

## 列表

| 编号 | 标题 | 状态 | 日期 |
|---|---|---|---|
| [ADR-000](ADR-000-template.md) | 模板 | 模板 | — |
| [ADR-001](ADR-001-tech-stack.md) | 技术栈：Vue3 + FastAPI + SQLite/PostgreSQL + ECharts（移动端见 ADR-005） | Accepted | 2026-11-06 |
| [ADR-002](ADR-002-data-model.md) | 数据模型：区域/指标/数据值规范化 | Proposed | 2026-11-06 |
| [ADR-003](ADR-003-agent-architecture.md) | Agent：受控工具 + ChartSpec，不生成 SQL/JS | Proposed | 2026-11-06 |
| [ADR-004](ADR-004-deployment-and-compliance.md) | 部署与合规：11.12 本地演示，粤政易后置 | Proposed | 2026-11-06 |
| [ADR-005](ADR-005-native-wechat-miniprogram.md) | 移动端改用原生微信小程序 | Accepted | 2026-11-06 |

## 写法

1. 背景：为什么现在决定？约束是什么？
2. 决策：选了什么？一句话说清。
3. 后果：得到什么、放弃什么、风险。
4. 备选：考虑过什么，为什么不选。
5. 实施要点：怎么落地。
6. 复审条件：什么情况下重新评估。
7. 链接：相关文档/任务。
