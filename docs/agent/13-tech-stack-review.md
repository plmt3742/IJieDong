---
owner: 项目开发者
last_updated: 2026-11-10
status: active
read_when: 技术选型复核；B-002 开工前；有人质疑“为什么不用 X”时
---

# 13 · 技术栈复审

> 结论先行：**原生微信小程序 + Vue3 后台 + FastAPI + SQLite（11.12 演示）/ PostgreSQL（生产）+ DeepSeek API + ECharts** 是当前约束下的最优组合。
> 约束：单人开发、11.12 要初步 demo、公职人员使用、后续接粤政易、数据以结构化指标为主、AI 只做受控问答。

## 1. 评价标准

| 标准 | 权重 | 说明 |
|---|---|---|
| 11.12 可交付 | 高 | 6 天内能跑通“导入→浏览→图表→问答” |
| 单人可维护 | 高 | 依赖少、文档多、调试直观 |
| 微信/粤政易兼容 | 高 | 原生小程序、工作台入口、后续 SSO |
| AI/数据能力 | 高 | 工具调用、图表、Excel、SQL |
| 长期可扩展 | 中 | 数据模型、指标扩展、权限、审计 |
| 信创/部署可迁移 | 中 | ARM64、国产库、私有化 LLM 预留 |
| 开发体验 | 中 | TypeScript、热更新、生态 |

## 2. 小程序：原生 vs uni-app vs Taro

| 维度 | 原生微信小程序 | uni-app | Taro |
|---|---|---|---|
| 微信兼容/性能 | 5/5 | 4/5 | 4/5 |
| 粤政易/微信生态 | 5/5 | 4/5 | 4/5 |
| 一套代码多端 | 2/5 | 5/5 | 4/5 |
| 开发速度（单人） | 3/5 | 5/5 | 4/5 |
| 调试/问题定位 | 5/5 | 3/5 | 3/5 |
| 包体/运行层 | 无额外运行层，最小 | 有运行层，包体较大 | 有运行层 |
| 生态/组件 | TDesign/Vant/WeUI 成熟 | uni-ui/uview | Taro UI/NutUI |
| 学习成本 | 低（官方文档） | 中（uni-app 语法/条件编译） | 中高（React/Taro 约束） |

**决策：原生微信小程序。**

理由：

1. 当前只要求微信小程序，**不需要 H5/App 多端**；uni-app/Taro 的最大优势用不上。
2. 原生对微信 API、包体、性能、审核、粤政易后续接入最稳；少一层运行层，问题少。
3. 用户明确要求原生；尊重决策，避免“为了技术而技术”。
4. 单人开发：原生官方文档/开发者工具最直接；出问题容易搜到答案。
5. 后台是独立 Web，不需要和小程序共享页面代码；共享的是 **API 类型**和 **ChartSpec**，这两者不依赖 uni-app。

代价与缓解：

| 代价 | 缓解 |
|---|---|
| 不能复用到 H5 | 本期不需要 H5；若粤政易强制 H5，再加一个薄 H5 壳（同一 API/ChartSpec） |
| 样板代码多 | 用 TypeScript + TDesign Miniprogram + 封装 request/chart 组件 |
| 图表适配 | 用 `echarts-for-weixin`（官方 ECharts 小程序封装）；必要时降级表格 |
| 后续 SSO | 小程序内走粤政易 SSO 需要平台支持；先本地登录，后期按接入文档改造 |

**小程序技术细节：**

- 语言：TypeScript + WXML + WXSS；`miniprogram-api-typings`。
- UI：**TDesign Miniprogram**（腾讯官方风格，组件全，适合政务）；必要时自定义主题。
- 图表：`echarts-for-weixin` + 自定义构建（减小包体）；后端只返回 ChartSpec。
- 网络：封装 `request`，统一 baseURL/token/错误码/loading。
- 构建：微信开发者工具 + npm 构建（TDesign/ECharts）；不引入重型框架。
- 目录：`miniprogram/pages`、`components`、`services`、`utils`、`types`、`images`、`styles`。

## 3. Web 后台

| 方案 | 优点 | 缺点 | 适合度 |
|---|---|---|---|
| **Vue3 + Vite + TS + Element Plus** | 中文资料多、表格/表单强、单人快 | 视觉偏传统、需定制 | 5/5 |
| React + Ant Design | 生态大、组件强 | 与小程序无共享；React 学习/心智负担 | 4/5 |
| Vue3 + Arco Design | 视觉好、字节生态 | 社区/资料少于 Element Plus | 4/5 |
| 低代码/Admin 模板 | 上手快 | 定制/权限/审计受限 | 2/5 |

**决策：Vue3 + Vite + TS + Element Plus。** 数据管理后台以表格/表单/导入/审计为主，Element Plus 最成熟；单人维护成本最低。视觉可通过 CSS 变量定制为政务风。

## 4. 后端

| 方案 | 优点 | 缺点 | 适合度 |
|---|---|---|---|
| **Python 3.13 + FastAPI** | LLM/数据生态好、开发快、OpenAPI 自动 | async/类型需要自律；Java 生态弱 | 5/5 |
| Node/NestJS | 全 TS、类型统一 | LLM/数据处理生态弱；框架重 | 3/5 |
| Java/Spring Boot | 政务常见、稳定 | 开发慢、样板多；LLM 生态弱 | 3/5 |
| Go/Gin | 性能/部署简单 | 数据/AI 生态弱；开发慢 | 2/5 |

**决策：FastAPI。** AI 是核心需求，Python 的 OpenAI 兼容 SDK、Excel、数据处理、评测脚本更直接；单人开发效率最高。若需求方强制 Java/信创中间件，再评估（见 §9）。

## 5. 数据库

| 方案 | 优点 | 缺点 | 适合度 |
|---|---|---|---|
| **SQLite（11.12 演示）** | 零安装、单文件、够用（1608 行） | 并发/权限/运维弱 | 5/5（演示） |
| **PostgreSQL 16（生产）** | 稳定、类型/JSON/分析强、SQLAlchemy 支持好 | 需安装/运维；信创需适配 | 5/5（生产） |
| MySQL 8 | 政务云常见、运维熟 | JSON/分析略弱；与 PG 取舍 | 4/5 |
| 国产库（金仓/达梦） | 信创合规 | 适配/资料/工具链成本 | 后置评估 |

**决策：双阶段。**

- **11.12 demo：SQLite**。数据量小（227 区域 × 15 指标），单用户演示；零安装，6 天内最稳。
- **生产：PostgreSQL 16**。多用户、审计、并发、备份；SQLAlchemy 可移植。
- 迁移：Alembic 同时支持 SQLite/PostgreSQL；避免 PG 特有语法；`JSON` 类型而非 `JSONB` 专用查询。
- 若需求方指定 MySQL/国产库：先做兼容 spike，再决定是否切换。

> 这不是“两套代码”，而是同一套 SQLAlchemy 模型 + 两个数据库 URL；演示用 SQLite，生产换 PostgreSQL。

## 6. LLM

**决策：DeepSeek API（OpenAI 兼容）+ 适配层。** 开发/演示直接用 DeepSeek；生产按数据密级切私有化/政务云模型。详见 [14-llm-deployment.md](14-llm-deployment.md)。

- 不在前端保存 Key；所有调用走服务端。
- 模型名/地址/Key 用环境变量；不写死供应商。
- 工具调用 + Pydantic/ChartSpec 校验；不让模型生成 SQL/JS。
- 失败/超时/额度不足有降级：缓存/重试/“请稍后再试”。

## 7. 图表

- **ECharts 5**；小程序用 `echarts-for-weixin`，后台用 `echarts`。
- 后端返回 **ChartSpec**，前端用固定渲染器；不返回 ECharts option/JS。
- 类型：柱、条形、饼、表格；有多年数据再加折线。
- 小程序包体：自定义构建 ECharts（只保留需要的图表/组件），避免全量包。

## 8. 认证与部署

- 后台：JWT + 用户名/密码；角色覆盖六类身份（见 `05` §9 与 `23`）。
- 小程序：微信登录（`wx.login` → 后端 `code2session`）+ 本地用户；开发期可用测试号/模拟登录。
- 粤政易：后期 SSO；`AuthProvider` 抽象，本地账号可回退。
- 11.12 演示：开发用本地进程，交付部署到用户小服务器（FastAPI + SQLite + Vite + 微信小程序实测），**不强依赖 Docker**（当前机器未安装 Docker）。
- 生产：Docker Compose / Nginx / PostgreSQL / HTTPS；政务外网另配。

## 9. 最终技术栈

| 层 | 选型 | 备注 |
|---|---|---|
| 小程序 | **原生微信小程序 + TypeScript + TDesign Miniprogram + echarts-for-weixin** | 用户决策；无 H5 |
| 后台 | **Vue3 + Vite + TS + Element Plus + ECharts** | 数据管理 |
| 后端 | **Python 3.13 + FastAPI + Pydantic v2 + SQLAlchemy 2.0 + Alembic** | OpenAPI |
| 数据库 | **SQLite（11.12 demo）/ PostgreSQL 16（生产）** | 同一模型 |
| LLM | **DeepSeek API（OpenAI 兼容）+ 适配层** | 生产可私有化 |
| 图表 | **ECharts + ChartSpec** | 跨端一致 |
| 包管理 | pnpm + uv（或 venv/pip 过渡） | 当前机器 uv 未安装 |
| 部署 | 本地进程（开发）→ 小服务器（Demo v0）→ Docker Compose（生产） | Docker 后置 |

## 10. 什么情况下需要改

| 触发 | 调整 |
|---|---|
| 粤政易强制 H5，不接受微信小程序 | 加薄 H5 壳（同 API/ChartSpec），或评估 uni-app/Taro 重做移动端 |
| 需求方强制 Java/国产中间件 | 后端改 Spring Boot；数据模型/API 不变 |
| 要求国产数据库 | PostgreSQL → 金仓/达梦适配 |
| 数据必须私有化 | DeepSeek API → vLLM/Ollama/政务云模型 |
| 并发/数据量大幅增长 | SQLite → PostgreSQL；加索引/缓存/队列 |
| 小程序图表包体超限 | ECharts 自定义构建；或 uCharts/表格降级 |

## 11. 11.12 可行性

6 天内做“完整系统”不现实；做**演示闭环**可行：

- 数据导入（Excel/演示数据）→ SQLite。
- 小程序：首页/区域/指标/基础图表。
- AI：3–5 个工具 + 问答 + ChartSpec。
- 后台：最小登录 + 数据列表/导入（可简化）。
- 文档/成本评估同步产出。

详细计划见 [15-demo-plan-1112.md](15-demo-plan-1112.md)。
