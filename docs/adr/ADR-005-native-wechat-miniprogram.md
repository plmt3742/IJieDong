# ADR-005: 移动端改用原生微信小程序

- 状态：Accepted
- 日期：2026-11-06
- 决策人：项目开发者（用户明确要求）
- 相关任务：MP-001~006、B-002
- 相关文档：`docs/agent/13-tech-stack-review.md`、`docs/agent/05-architecture.md`

## 1. 背景

原 ADR-001 建议移动端用 uni-app（Vue3 + TS），同时构建微信小程序 + H5，理由是“一套代码多端、粤政易支持 H5”。

用户明确要求：**小程序使用原生微信小程序构建**。同时确认：

- 用户对象是公职人员；
- 微信小程序后续接入粤政易工作台；
- 粤政易等程序搭建完再接；
- 当前没有 H5 多端需求。

因此需要复审：原生小程序是否适合，其他技术栈是否仍最优。

## 2. 决策

移动端改为：

- **原生微信小程序 + TypeScript + WXML/WXSS**
- UI：**TDesign Miniprogram**（腾讯官方风格，政务适配）
- 图表：**echarts-for-weixin**（ECharts 官方小程序封装，自定义构建减小包体）
- 网络：自封装 `request`（baseURL/token/错误码/loading）
- 构建：微信开发者工具 + npm 构建
- 不做 H5；若粤政易强制 H5，后续加薄 H5 壳（同一 API/ChartSpec）

其余栈维持：

- 后台：Vue3 + Vite + TS + Element Plus
- 后端：Python 3.13 + FastAPI + SQLAlchemy 2.0 + Alembic
- 数据库：SQLite（11.12 demo）/ PostgreSQL 16（生产）
- LLM：DeepSeek API（OpenAI 兼容）+ 适配层
- 图表契约：ChartSpec（跨端一致）

## 3. 后果

### 正面

- 微信兼容/性能最好；少一层运行层，问题少。
- 官方文档/开发者工具直接；单人排错快。
- 包体可控；审核/粤政易接入风险低。
- 用户明确要求，减少沟通成本。

### 负面/代价

- 不能复用到 H5/App；如果粤政易强制 H5，需要补薄 H5 壳。
- 样板代码比 uni-app 多；需要封装 request/组件/图表。
- 后台与小程序不能共享页面代码；只共享 API 类型/ChartSpec。

### 风险与缓解

| 风险 | 缓解 |
|---|---|
| 小程序图表包体/兼容 | ECharts 自定义构建；表格降级；早期 spike |
| 粤政易要求 H5 | 薄 H5 壳（同 API/ChartSpec）；或届时评估 uni-app/Taro |
| 原生开发慢 | TypeScript + TDesign + 组件封装；AI 辅助 |
| SSO 接入复杂 | AuthProvider 抽象；先本地登录，后期按粤政易文档改造 |

## 4. 备选方案

| 方案 | 优点 | 缺点 | 为什么没选 |
|---|---|---|---|
| uni-app | 一套代码多端；开发快 | 运行层/包体/兼容坑；当前无 H5 需求 | 用户要求原生；多端优势用不上 |
| Taro + React | 多端；React 生态 | 运行层/约束；与后台 Vue 不统一 | 同上 |
| 原生 + H5 双端 | 最灵活 | 两套代码；单人成本高 | 当前不需要 H5 |
| 原生 + WebView 套 H5 | 复用一个 H5 | 体验/审核/性能差 | 不推荐 |

## 5. 实施要点

1. `apps/mp` 使用原生结构：`project.config.json` + `miniprogram/`（pages/components/services/utils/types/images/styles）。
2. TypeScript + `miniprogram-api-typings`；npm 构建 TDesign/ECharts。
3. 封装 `services/request.ts`：baseURL、token、错误码、loading、重试。
4. 图表组件：`components/chart/` 包装 echarts-for-weixin，输入 ChartSpec，输出 canvas。
5. 小程序登录：`wx.login` → 后端 `code2session`；开发期可用测试号/模拟。
6. 不在小程序保存 DeepSeek Key/数据库密码；所有 AI 请求走后端。
7. 早期验证：首页 + 一张柱状图 + 一次 API 请求；确认包体/开发者工具构建。

## 6. 复审条件

- 粤政易明确要求 H5 且不接受微信小程序 → 加 H5 壳或重评 uni-app/Taro。
- 原生开发在 11.12 前无法完成主路径 → 评估降级方案（H5 套壳/减页面）。
- 小程序图表包体/性能不达标 → 换 uCharts/表格降级。
- 需要同时上微信小程序 + 独立 App → 重新评估跨端框架。

## 7. 链接

- `docs/agent/13-tech-stack-review.md`
- `docs/agent/15-demo-plan-1112.md`
- `docs/adr/ADR-001-tech-stack.md`（后端/后台/数据库部分仍有效）
- `docs/agent/05-architecture.md`
