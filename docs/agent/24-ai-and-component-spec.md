---
owner: 项目开发者
last_updated: 2026-11-10
status: draft
read_when: 实现或评审 AI 问答、AnswerBlocks、意图路由、工具白名单、问答评测前
---

# 24 · AI 与 AnswerBlocks 契约（草案）

> 状态：**契约草案，待实现**。本文展开 [05-architecture.md](05-architecture.md) §7/§8 与 [ADR-003](../adr/ADR-003-agent-architecture.md)，不替代它们。
> 事实源顺序：API 路径与错误码以 05 §6 为准；组件元数据以 [07 组件库规范](../product/07-component-library-spec.md) 为准；导出以 [25 导出规范](25-export-spec.md) 为准；本文负责"模型输出什么、如何校验、如何兜底"。
> 11.12 是可在用户小服务器部署运行的 Demo v0。多维、时序、地理、关系分析属 M1；本文对 M1 类型只做契约预留与 11.12 明确降级。
> 文中 JSON 数值均为**结构示例**，不是真实统计，禁止作为数据引用。

## 1. 目标、范围、非目标

### 1.1 目标

1. 让模型只输出**结构化、可校验、可复现**的答案，不输出 SQL、JavaScript、ECharts option 或 HTML。
2. 用 `AnswerEnvelope` 与 `AnswerBlock` 固定"答案由哪些块组成"，前端用**静态组件 + 通用 schema 渲染器**展示。
3. 用意图分类约束"同类问题得到同一种展示"，减少模型自由发挥。
4. 用白名单只读工具把取数与计算固定在服务端，模型只负责理解、选工具与表达。
5. 明确循环预算、校验分层、重试与确定性兜底、护栏和评测口径，使实现可验收。

### 1.2 范围

- `POST /ai/chat` 的响应结构（在 05 §6.2 响应上扩展 `intent`、`blocks`、`actions`、`meta`）。
- 11.12 的 10 类 `AnswerBlock` 与对应组件（组件清单与 props schema 见 07）。
- 10 个核心只读工具的语义、参数、返回与上限。
- Agent 循环预算、四层校验、一次重试、确定性兜底。
- 50 题评测集（30 可答 + 10 无数据 + 10 越界）与指标。

### 1.3 非目标

- 不做运行时动态组件加载、远程 JS、`eval`、模板字符串编译（边界见 07 §1）。
- 不做 Text-to-SQL、任意代码执行、任意 HTTP 请求、文件读写。
- 不做预测、归因或因果推断；`relationship` 在 11.12 明确不提供。
- 不做多模态问答、流式 token 渲染；11.12 用整体返回加阶段状态提示。
- 不定义视觉规范；颜色、字号、间距由 07 与 UE 文档决定。

## 2. AnswerEnvelope

### 2.1 结构

`data` 顶层即 AnswerEnvelope。字段顺序固定，便于快照与哈希。

```json
{
  "answer_id": "ans_20261110_0001",
  "answer_markdown": "2025 年常住人口排名前 5 的镇街为……（示例文本，非真实统计）",
  "intent": "rank",
  "blocks": [
    {
      "id": "b1",
      "type": "ranking",
      "component": "ranking_bar",
      "props": {
        "title": "2025 年镇街常住人口（前 5）",
        "unit": "人",
        "period": "2025",
        "order": "desc",
        "items": [
          {"rank": 1, "region_code": "JD-QX", "region_name": "曲溪街道", "value": 185000, "citation_id": "c1"},
          {"rank": 2, "region_code": "JD-YL", "region_name": "云路镇", "value": 142000, "citation_id": "c1"}
        ]
      },
      "data_ref": {
        "indicator_codes": ["population_resident"],
        "region_codes": [],
        "periods": ["2025"],
        "level": "town",
        "tool_call_id": "tc_1"
      },
      "fallback": {
        "type": "table",
        "component": "data_table",
        "props": {"columns": ["排名", "区域", "常住人口（人）"], "rows": [["1", "曲溪街道", 185000]]}
      }
    },
    {
      "id": "b2",
      "type": "source",
      "component": "source_card",
      "props": {"citation_ids": ["c1"], "data_as_of": "2026-11-10", "generated_at": "2026-11-10T10:00:00+08:00"},
      "data_ref": null,
      "fallback": {"type": "text", "component": "text", "props": {"variant": "body", "paragraphs": ["数据来源见引用。"]}}
    },
    {
      "id": "b3",
      "type": "actions",
      "component": "action_row",
      "props": {
        "actions": [
          {"type": "drilldown", "label": "查看指标", "target": {"page": "MP04", "params": {"indicator_code": "population_resident", "period": "2025"}}},
          {"type": "export", "label": "导出本页", "target": {"source": "answer"}, "permission": "export"}
        ]
      },
      "data_ref": null,
      "fallback": null
    }
  ],
  "citations": [
    {
      "id": "c1",
      "indicator_code": "population_resident",
      "indicator": "常住人口",
      "region_level": "镇街",
      "period": "2025",
      "source": "data_values",
      "data_as_of": "2026-11-10"
    }
  ],
  "actions": [
    {"type": "export", "label": "导出本页", "target": {"source": "answer"}, "permission": "export"}
  ],
  "follow_up_questions": ["要看户籍人口吗？", "要不要和面积一起看？"],
  "meta": {
    "request_id": "req_20261110_0001",
    "model": "deepseek-chat",
    "latency_ms": 4210,
    "tool_calls": 2,
    "data_version": "dv_20261110_01",
    "data_hash": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
    "registry_version": "1.0.0",
    "generated_at": "2026-11-10T10:00:00+08:00",
    "degraded": false,
    "locale": "zh-CN"
  }
}
```

### 2.2 字段说明

| 字段 | 类型 | 必填 | 约束与说明 |
|---|---|---|---|
| `answer_id` | string | 是 | 服务端生成，全局唯一；导出与审计的主键来源 |
| `answer_markdown` | string | 是 | ≤2000 字；仅允许 Markdown 子集（段落、有序/无序列表、加粗、行内代码）；禁止 HTML、图片、外链 |
| `intent` | enum | 是 | 见 §4；只用于展示选择、埋点与兜底，**不得**作为数字依据 |
| `blocks` | object[] | 是 | 1–8 个；顺序即展示顺序；每个块必须能独立渲染；无数据时至少 1 个 `notice` 块 |
| `citations` | object[] | 是 | ≥1；`id` 在 Envelope 内唯一；所有数值块必须引用已存在的 `citation_id` |
| `actions` | object[] | 否 | ≤3；规范化动作列表，`actions` 块是它在界面上的投影；类型白名单见 07 §7 |
| `follow_up_questions` | string[] | 否 | ≤3；每条 ≤30 字；不得包含新的数字断言 |
| `meta.request_id` | string | 是 | 与 05 §6.1 的 `request_id` 一致 |
| `meta.model` | string | 是 | 模型标识；不记录 Key |
| `meta.latency_ms` | int | 是 | 端到端耗时（含工具） |
| `meta.tool_calls` | int | 是 | 实际工具调用次数，用于预算审计 |
| `meta.data_version` | string | 是 | 数据版本（导入批次或快照版本） |
| `meta.data_hash` | string | 是 | 本答案所依赖数据的规范化哈希；导出复现依据（见 25 §4） |
| `meta.registry_version` | string | 是 | 组件注册表版本（见 07 §8） |
| `meta.generated_at` | string | 是 | ISO 8601，带时区（+08:00） |
| `meta.degraded` | bool | 是 | 是否走了降级（兜底模板、无 LLM、组件降级） |
| `meta.locale` | string | 是 | 11.12 固定 `zh-CN` |

引用对象要求：`id`、`indicator`、`period`、`region_level`、`source` 为 05 已约定的最小集；本文新增 `indicator_code` 与 `data_as_of`，用于跳转与时效说明。若引用到具体区域，补 `region_code`、`region_name`。

### 2.3 与 05 `chart_spec` 的兼容

05 §7.5 当前输出契约为 `answer_markdown` + `chart_spec` + `citations` + `follow_up_questions`。本契约以 `blocks` 为**权威结构**，`chart_spec` 降级为兼容字段：

1. `blocks` 存在时，客户端忽略 `chart_spec`。
2. `blocks` 缺失时（旧客户端或灰度期），服务端从 `chart_spec` 生成单个 `chart` 或 `table` 块再返回。
3. 11.12 仍返回 `chart_spec`，内容由第一个图表类块推导，保证旧页面可用；计划在 11.12 后一个版本移除。
4. 该变更需主 agent 在 05 §7.5 登记，本文不修改 05。

## 3. AnswerBlock

### 3.1 通用字段

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 是 | `b1`–`b8`，Envelope 内唯一，顺序稳定 |
| `type` | enum | 是 | `summary` / `metric_grid` / `chart` / `table` / `ranking` / `comparison` / `insight` / `source` / `notice` / `actions` |
| `component` | string | 是 | 注册表 key（如 `ranking_bar`）或渲染器原语 id（如 `text`）；解析顺序见 07 §6 |
| `props` | object | 是 | 已解析的最终展示值；渲染器**不再查库**；数值必须来自工具结果 |
| `data_ref` | object/null | 否 | 审计、导出与权限复核用；不参与渲染 |
| `fallback` | object/null | 否 | 更简单类型的块；最多一层；`null` 表示失败时退到 `notice` |

`data_ref` 字段：`indicator_codes[]`、`region_codes[]`、`periods[]`、`level`、`tool_call_id`。

### 3.2 类型与 props

| type | 默认 component | 关键 props | 数据条件 | 11.12 |
|---|---|---|---|---|
| `summary` | `text`（`variant=summary`） | `title?`、`paragraphs[]`、`highlights?[]` | 可有数字，但每个数字必须带 `citation_id` 或整体引用 | 提供 |
| `metric_grid` | `metric_grid` | `title?`、`columns?`（2–4）、`items[{label,value|null,unit,delta?,delta_label?,status?,citation_id}]` | 1–6 个指标；值可空，空显示“无数据” | 提供 |
| `chart` | `bar_chart` / `line_chart` / `pie_chart` | `chart_type`、`title`、`unit`、`categories[]`、`series[{name,values[]}]`、`sort?`、`max_items?` | 仅数值指标；类别 ≤15；`null` 保留为无数据 | 柱/条提供；折线/饼图 P1 |
| `table` | `data_table` | `title?`、`columns[]`、`rows[][]`、`unit?`、`align?` | 行 ≤100；单元格为 string / number / null | 提供 |
| `ranking` | `ranking_bar` | `title`、`unit`、`period`、`order`、`items[{rank,region_code,region_name,value,citation_id}]`、`include_development_zones?` | 同一指标、同一层级、同一期；有效值 ≥3；排名连续 | 提供 |
| `comparison` | `comparison_board` | `title`、`indicator`、`unit`、`period`、`items[{region_code,region_name,value,diff_from?,diff_pct?}]`、`baseline?` | 2–6 个区域、同一指标同一期 | P1；11.12 用 `data_table` |
| `insight` | `text`（`variant=insight`） | `text`、`basis_citation_ids[]`、`confidence?` | 不得引入新数字；必须标注“分析判断，仅供参考” | P1，默认关闭 |
| `source` | `source_card` | `citation_ids[]`、`data_as_of`、`generated_at` | 每个 Envelope 至少 1 个 | 提供 |
| `notice` | `text`（`variant=notice`） | `level`（`info`/`warning`/`nodata`/`refused`）、`code`、`text`、`suggestions?[]` | 无数据、拒答、覆盖不足、降级时必须出现 | 提供 |
| `actions` | `action_row` | `actions[{type,label,target,permission?}]` | 类型白名单见 07 §7；≤3 | 提供 |

### 3.3 数量与体积上限

| 项 | 上限 | 超出行为 |
|---|---:|---|
| `blocks` | 8 | 截断并追加 `notice`（`warning`，`BLOCKS_TRUNCATED`） |
| `table.rows` | 100 | 截断并在 `props.truncated=true` 标注“仅显示前 100 行” |
| `chart.categories` / `series` | 15 / 3 | 合并尾部为“其他”或改表格 |
| `ranking.items` | 15 | 截断，`props.truncated=true` |
| `comparison.items` | 6 | 超出改 `data_table` |
| `metric_grid.items` | 6 | 超出改 `metric_grid` 两页或表格 |
| 单块 `props` 序列化 | 16 KB | 该块降级为 `fallback` |
| 整个 Envelope | 128 KB | 截断块并追加 `notice` |
| `answer_markdown` | 2000 字 | 截断并提示“完整内容见导出” |

### 3.4 校验要求

1. `component` 必须能解析到注册表 key 或原语；解析失败 → `fallback`。
2. `props` 必须通过该组件的 `props_schema`（`additionalProperties=false`）。
3. `props` 中每个数值必须能在本次工具结果中找到（允许按声明精度四舍五入）；找不到 → 校验失败。
4. 文本指标（`value_type=text`）不得出现在 `chart` / `ranking` / `comparison`。
5. `null` 不得被替换为 0；需要“0”时必须有工具明确返回值 0。
6. `source` 块与 `citations` 必须一致；不得出现未被任何块引用的“装饰性引用”。

## 4. 意图分类

### 4.1 分类表

| intent | 典型问法 | 默认组件 | 必要条件 | 不满足时 |
|---|---|---|---|---|
| `lookup` | “2025 年曲溪街道常住人口是多少？” | `metric_card`（多指标用 `metric_grid`）或 `text` | 区域、指标、期唯一确定 | `clarify` |
| `rank` | “哪个镇面积最大？”“常住人口前 5” | `ranking_bar` | 可排名数值指标；同层级有效值 ≥3 | `notice` + `data_table` |
| `compare` | “曲溪和云路的面积差多少？” | `comparison_board`（P1）/`data_table` | 2–6 区域、同一指标同一期 | `data_table` |
| `trend` | “近五年常住人口变化” | `line_chart`（P1） | ≥2 个可比期、口径一致 | `notice` + 单期值 |
| `composition` | “各镇街面积占比” | `pie_chart`（P1）/`ranking_bar` | 同一父级全集、占比有意义、≤8 类 | `ranking_bar` |
| `profile` | “介绍一下玉湖镇” | `text_profile` + `metric_grid` | 有文本指标或关键指标 | `notice` |
| `relationship` | “人口和 GDP 有关系吗？” | 无（M1） | 同层级同期成对有效值 n≥8 | 11.12 明确 `refuse` |
| `export` | “导出这张图”“生成 PDF” | `action_row` + `notice` | 已有答案快照且用户有导出权限 | 403 或引导登录 |
| `clarify` | “这个镇有多少人？”（指代不明） | `text`（`variant=clarify`）+ `action_row` | 缺少区域/指标/期之一 | 最多追问 1 个问题 |
| `refuse` | “预测明年 GDP”“帮我查某人的信息” | `notice`（`level=refused`） | — | — |

### 4.2 判定规则

1. **规则优先**：先做实体解析与关键词/句式规则（时间、排名、对比、占比、导出、预测），规则命中且置信度 ≥0.8 直接采用。
2. **模型分类**：规则未命中时由 LLM 输出 `intent`，置信度 <0.6 → `clarify`。
3. **优先级**：安全与越界 > `export` > `profile` > `rank`/`compare`/`trend`/`composition` > `lookup` > `clarify`。冲突时取更保守的一侧。
4. **期默认值**：未指定期时使用"最新已发布且有数据"的期，并在答案首句写明；不得默认 2025 而不说明。
5. **坐标不猜**：区域/指标无法唯一解析时不得猜测，必须 `clarify`；别名映射只走 `region_aliases`。

### 4.3 确定性兜底映射

LLM 不可用、超时或输出非法时，用最后一次成功工具结果的形状直接选组件，不重新生成数字：

| 工具结果形状 | 组件 |
|---|---|
| 单区域单指标单期标量 | `metric_card` + `text` |
| 一组排名行 | `ranking_bar` |
| 多区域同一指标 | `data_table`（P1 起 `comparison_board`） |
| 有序期序列 ≥2 | `line_chart`（P1）否则 `metric_grid` |
| 区域画像（文本 + 关键指标） | `text_profile` + `metric_grid` |
| 无数据 / 覆盖不足 / 工具禁用 | `notice` |
| 无任何工具结果 | `notice`（`refused`，`NO_DATA`） |

## 5. 工具白名单

### 5.1 核心工具（10 个，只读）

| 工具 | 参数 | 返回 | 限制 |
|---|---|---|---|
| `resolve_entities` | `text`、`kind?`（region/indicator）、`level?`、`limit?` | 候选 `[{kind,code,name,level,score}]` | ≤10；低于阈值不自动采用 |
| `describe_dataset` | `indicator_code?`/`indicator_codes[]`、`region_code?`、`period?` | 指标元数据、单位、适用层级、可用期、覆盖率、来源 | ≤10 个指标 |
| `query_observations` | `indicator_codes[]`、`region_codes[]`、`periods[]?` | `[{region_code,indicator_code,period,value,unit,citation_id}]` | ≤500 行；区域 ≤20；期 ≤5 |
| `rank_regions` | `indicator_code`、`period`、`level`、`order`、`limit`、`include_development_zones?` | 排名行（`rank`、区域、值） | `limit` ≤15；有效值 ≥3；空值排除 |
| `compare_regions` | `indicator_code`、`region_codes[2..6]`、`period` | 行 + 绝对差/相对差 | 区域 ≤6；同指标同期 |
| `trend_values` | `indicator_code`、`region_codes[1..5]`、`periods[]` | 序列 `[{region_code, points:[{period,value}]}]` | 期 ≥2；11.12 返回 `NOT_ENOUGH_PERIODS` |
| `composition` | `indicator_code`、`period`、`level`、`parent_code?` | 部分 + 合计 + 占比 | 父级覆盖完整；否则 `PARTIAL_COVERAGE` |
| `get_region_profile` | `region_code`、`period?` | 文本字段 + 关键指标 ≤6 + 引用 | 单区域 |
| `compute_metric` | `formula`（share/per_capita/growth/diff）、`inputs{}` | 计算值 + 公式说明 | 仅白名单公式；输入必须来自工具结果 |
| `correlation` | `indicator_x`、`indicator_y`、`level`、`period` | `{n,coefficient,method}` | M1；11.12 `TOOL_DISABLED`；n≥8 |

### 5.2 名称处置

任务清单里另出现 4 个名字，本契约按最小权限拆开，不把它们都做成 LLM 工具：

| 名称 | 处置 | 理由 |
|---|---|---|
| `render_component` | 服务端组装/校验步骤 | 渲染不是取数；模型不应触发任意组件渲染 |
| `export_view` | 用户动作 `POST /exports` | 导出涉及权限与文件生成，由用户显式触发（见 25） |
| `clarify` | 输出意图 `intent=clarify` | 追问是输出形态，不是数据访问 |
| `refuse` | 输出意图 `intent=refuse` + `notice` | 拒答是输出形态，不是数据访问 |

`list_regions` / `list_indicators` / `get_indicator_values` / `build_chart`（05 §7.3 的旧名）在实现时合并进 `resolve_entities`、`describe_dataset`、`query_observations` 与组件选择；旧名不再暴露给模型。

### 5.3 禁止与错误

禁止：`execute_sql`、`http_request`、`read_file`、`write_file`、任意代码执行，以及任何以字符串传入 SQL/JS/表达式/URL 的参数。

工具错误统一返回 `{"error":{"code","message","hint"}}`，错误计数计入预算：

| code | 含义 |
|---|---|
| `INVALID_ARGS` | 参数缺失/类型错误/越界 |
| `NOT_FOUND` | 区域/指标不存在 |
| `NOT_APPLICABLE` | 指标不适用于该层级 |
| `NO_DATA` | 该区域/指标/期无数据 |
| `NOT_ENOUGH_PERIODS` | 期数不足，无法做趋势 |
| `PARTIAL_COVERAGE` | 父级部分缺失，占比不可计算 |
| `LIMIT_EXCEEDED` | 超过行数/区域数上限 |
| `TOOL_DISABLED` | 该工具在当前版本关闭（如 `correlation`） |

## 6. Agent 循环

### 6.1 流程

```text
POST /ai/chat
  → 鉴权/会话加载/可见范围
  → 规则层：实体解析 + 意图先验
  → LLM（system + 历史摘要 + 工具 schema）
  → tool_calls（白名单、参数校验、行数上限）
  → 工具执行（只读、写审计、返回 citation_id）
  → LLM 最终 JSON（AnswerEnvelope）
  → L1 JSON 解析 → L2 Pydantic → L3 props_schema
  → L4 引用/数据溯源 → L5 策略校验
  → 失败：带错误重试 1 次
  → 仍失败：确定性兜底（§4.3）
  → 落库 chat_messages/audit + 返回
```

### 6.2 预算与超时

| 项 | 11.12 值 | 说明 |
|---|---:|---|
| 单轮工具调用 | 5 | 与 05 §7.2、ADR-003 一致；提高到 8 需改 ADR 与 05 |
| 端到端超时 | 30 s | 超时返回 `AI_TIMEOUT` 与可重试提示 |
| LLM 单次超时 | 20 s | 适配层配置，不写死供应商 |
| 单工具超时 | 3 s | 查询走索引；超时视为 `LIMIT_EXCEEDED` 之外的独立错误 |
| 历史轮次 | 6 轮 | 超出做摘要，不整段拼接 |
| 输出 token | ≤1200 | 与 2000 字答案上限匹配 |
| 答案长度 | 2000 字 | 超出截断并提示 |
| 校验重试 | 1 次 | 仅重试最终 JSON，不重跑全部工具 |
| 并发/限流 | 按用户 3/min、IP 20/min | 返回 `RATE_LIMITED` |

### 6.3 五层校验

| 层 | 内容 | 失败处理 |
|---|---|---|
| L1 | JSON 可解析、UTF-8 | 重试 1 次 |
| L2 | `AnswerEnvelope` / `AnswerBlock` Pydantic 校验 | 重试 1 次；仍失败 `AI_INVALID_OUTPUT` |
| L3 | 每个组件 `props_schema`（含上限） | 该块降级 `fallback`；无 fallback 则转 `notice` |
| L4 | 引用完整、`citation_id` 存在、`data_ref` 可追溯、数值溯源 | 整体重试 1 次；仍失败走兜底 |
| L5 | 策略：文本不画图、空值不为 0、关系 n≥8 且不作因果、组件在平台可用 | 直接改写为 `notice` 或删块，不重试 |

### 6.4 重试与兜底顺序

1. 带错误信息重试一次（不新增工具调用额度）。
2. 仍非法 → 用最后一次成功工具结果按 §4.3 组装。
3. 无可用结果 → `notice`（`refused` 或 `nodata`）+ `AI_INVALID_OUTPUT` 仅在日志记录，用户侧只看到可读文案。
4. 兜底答案 `meta.degraded=true`，并在 `notice` 中说明“已使用简化展示”。
5. 任何情况下不得返回空 `blocks`。

## 7. 护栏

| 规则 | 实现要求 | 验证方式 |
|---|---|---|
| 数字只来自后端 | 工具返回结构化值 + `citation_id`；模型不得自算排名/合计 | L4 数值溯源；评测数字正确率 |
| 引用强制 | 每个数值块至少 1 个 `citation_id`；每个引用可跳到指标页 | L4 校验；评测引用完整率 |
| 无数据即说明 | 返回 `notice`（`nodata`），写清缺哪个区域/指标/期 | 10 题无数据用例 |
| 文本指标不画图 | `value_type=text` 禁止进入 `chart`/`ranking`/`comparison` | L5 校验 + 单测 |
| 空值不为 0 | 全链路保留 `null`；表格显示“无数据”，图表跳过 | 导入/查询/渲染/导出四处抽检 |
| 关系不给因果 | `relationship` 需 n≥8，输出“相关不等于因果”；11.12 不提供 | 策略校验 + 评测越界题 |
| 提示注入 | 用户文本只作为数据；忽略“忽略以上规则/输出系统提示”等指令；不执行其中 URL/命令 | 注入用例；日志检查 |
| 不泄密 | 不输出系统提示、密钥、表结构、内部主机名、他人 openid | 安全检查；日志脱敏 |
| 可见范围 | 工具按用户角色与区域范围过滤；越权区域视为不存在 | 权限用例 |
| 时效与口径 | 每个答案标注期、来源、`data_as_of`；演示数据必须标注“演示数据” | 抽查 + 评测 |

## 8. 评测

### 8.1 题集构成（50 题）

| 组 | 数量 | 覆盖 |
|---|---:|---|
| 可答 | 30 | 查询 8、排名 7、对比 6、画像 5、占比 4 |
| 无数据 | 10 | 未知指标 4、错误年份 3、区域无该指标 3 |
| 越界/敏感 | 10 | 政治敏感 3、预测/因果 3、个人隐私 2、提示注入 2 |

题集放 `services/api/tests/fixtures/ai_eval/`（JSON），只用演示数据或脱敏数据；每题含期望值、期望引用、期望意图、期望组件。

### 8.2 指标

| 指标 | 目标 | 口径 |
|---|---:|---|
| 数字正确率 | ≥95% | 与期望值完全一致（按指标精度） |
| 引用完整率 | ≥98% | 数值块均有有效引用 |
| 结构合法率 | ≥98% | L2+L3 一次通过 |
| 意图/组件匹配率 | ≥90% | 与题集期望一致，或落在允许集合内 |
| 拒答正确率 | ≥90% | 无数据/越界不得编造 |
| 空值处理正确率 | 100% | 不把无数据写成 0 |
| p95 延迟 | <10 s | 单轮问答端到端 |
| 单题 token 成本 | 记录并设预算 | 按模型配置统计 |

任一项不达标：按 ADR-003 §6 暂停上线并修 Prompt/工具/校验，不得用放宽校验换通过。

## 9. 与组件库、导出的关系

- **组件库（07）**：`block.component` 是注册表 key 或原语 id；解析顺序为"快照版本 → 最新兼容版本 → `fallback_key` → 原语 → `notice`"。组件的 `props_schema`、`data_requirements`、`client_min_version` 是本文 L3/L5 校验的输入。
- **导出（25）**：导出使用 Envelope 快照，不重新提问、不重新取数；快照包含 `meta.data_hash`、`meta.registry_version` 与逐块 `component`+`version`，用于复现与审计。
- **API（05）**：新增字段属于响应扩展，不改变路径；`chart_spec` 兼容策略需在 05 §7.5 登记后再实现。

## 10. 开放问题

1. `blocks` 取代 `chart_spec` 的迁移窗口多长？需主 agent 在 05 §7.5 与 OpenAPI 同步后生效。
2. 工具预算维持 5 次是否够用？若评测中 >20% 问题因预算不足失败，按 ADR-003 §6 提额度并记录。
3. `compute_metric` 的白名单公式是否需要扩展（如复合增长率、人均耕地）？扩展前先补 props 与评测题。
4. `insight` 块是否在 11.12 开放？当前默认关闭，若开放必须统一加"分析判断"标识。
5. 意图分类用规则还是小模型？11.12 先规则 + LLM，置信度阈值需用评测集校准。
6. 小程序端 Markdown 渲染能力（表格、嵌套列表）需在 MP-001 阶段验证；不支持时降级为纯段落。
