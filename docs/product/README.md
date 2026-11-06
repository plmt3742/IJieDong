# 产品文档

> 本目录放“做什么、给谁用、怎么走”的产出；技术契约在 `docs/agent/05-architecture.md`，不要混。

## 文档清单

| 文件 | 内容 | 状态 |
|---|---|---|
| [01-prd-lite.md](01-prd-lite.md) | 一页纸 PRD：问题、用户、价值、闭环、P0/P1/P2、指标 | 初稿 |
| [02-ia-and-flows.md](02-ia-and-flows.md) | 信息架构、页面清单、3 条核心流程、AI 状态机 | 初稿 |
| [03-page-specs.md](03-page-specs.md) | 页面规范模板 + 核心页面清单 | 模板/部分 |
| [04-data-catalog.md](04-data-catalog.md) | 数据模板分析：区域、指标、质量、导入规则 | 初稿 |
| [05-page-structure.md](05-page-structure.md) | 页面清单、跳转/数据传递、页面详情 | 初稿 |
| [ue/page-map.html](ue/page-map.html) | 18 页低保真线框 + 可缩放/可点击页面地图 | 可验证 |
| [ue/wireframes.html](ue/wireframes.html) | 18 页灰度线框总览 | 可验证 |

## 产品原则

1. **数据可信优先**：宁可不答，不可编造；图表必须能追溯到指标/区域/年份。
2. **移动端先看数**：首页到指标 ≤3 次点击；图表清楚，不堆装饰。
3. **后台先能维护**：导入、修订、审计是数据产品的地基。
4. **AI 是入口不是噱头**：问答要能落到数据表和图表，不能只聊天。
5. **政务场景克制**：不做花哨动效/社交/游戏化；可读性、稳定性、合规优先。

## 状态

- 当前为 **M0.5（11.12 初步 demo）** 初稿，未经过需求方评审。
- 已确认：公职人员、原生微信小程序、粤政易后置、Excel/接口/手工、DeepSeek API。
- 仍需确认的问题与对外话术：`docs/agent/12-open-questions.md`、`docs/agent/17-outreach-copy.md`。
- 11.12 范围/排期：`docs/agent/15-demo-plan-1112.md`。
