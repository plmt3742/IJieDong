# 07 · 组件库规范（Component Registry）

> 状态：**契约草案，待实现**。本文与 [24 AI 与 AnswerBlocks 契约](../agent/24-ai-and-component-spec.md)、[25 导出规范](../agent/25-export-spec.md)配套。
> 适用范围：11.12 Demo v0 的 AnswerBlocks 渲染、AI 组件选择、管理端组件管理、导出渲染。
> 本文只定义**元数据契约与渲染边界**，不定义视觉风格；颜色、字号、间距在 UE 文档冻结后补充。

## 1. 目标与边界

### 1.1 目标

1. 用一份可校验的**组件注册表**（metadata registry）描述"有哪些组件、用在哪、接受什么 props、导出成什么"。
2. 让 AI 只能从注册表选择组件，props 由后端按 `props_schema` 校验，前端按固定渲染器展示。
3. 让组件版本、启用状态、最低客户端版本成为可治理的数据，而不是散落在代码里的硬编码。
4. 让同一份 AnswerBlocks 在小程序、后台、导出三条链路上表现一致。

### 1.2 边界

| 项 | 结论 |
|---|---|
| 注册表是什么 | 后端存储的 JSON 清单（manifest）+ 校验 schema，**不是可执行代码** |
| 是否运行时下载组件 | 否。小程序与后台的渲染器随版本发布，注册表只决定"用哪个已内置组件" |
| 新增渲染代码 | 必须发版（小程序提审/后台构建）；后台可先灰度 |
| 后端能做什么 | 存储 manifest、props schema、示例、版本、启用/禁用；向客户端下发组件 key、版本与 props |
| 后端不能做什么 | 下发 JS、模板字符串、表达式、远程组件包；不能改变 props 语义 |
| AI 能做什么 | 选择组件 key、生成 props 值（必须来自工具结果） |
| AI 不能做什么 | 新增组件、修改 schema、指定任意样式、注入事件处理器 |

### 1.3 非目标

- 不做低代码页面搭建器、不做任意布局 DSL、不做用户自定义组件。
- 不做组件市场、不做跨项目复用、不做第三方插件。
- 不做 M1 的地图、散点、桑基、时间轴等组件；相关 key 仅保留命名空间。

## 2. 注册表字段

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `key` | string | 是 | 全局唯一，`snake_case`，如 `ranking_bar`；发布后不可改名 |
| `version` | string | 是 | 语义化版本 `MAJOR.MINOR.PATCH`；同一 key 多版本共存 |
| `name` | string | 是 | 中文显示名，≤20 字 |
| `category` | enum | 是 | `metric` / `text` / `chart` / `table` / `ranking` / `comparison` / `source` / `action` / `composite` |
| `description` | string | 是 | 一句话说明"是什么"，≤80 字，给管理员看 |
| `when_to_use` | string | 是 | 一句话说明"什么时候用"，≤80 字，给 AI 选择与意图兜底用 |
| `props_schema` | object | 是 | JSON Schema（draft 2020-12 子集）；`additionalProperties=false`；含数量上限 |
| `data_requirements` | object | 是 | 数据前置条件，如指标类型、层级、期数、最小样本、覆盖完整性 |
| `example_props` | object | 是 | 必须能通过 `props_schema`；用于预览与测试 |
| `renderer` | object | 是 | `{"mp": "<小程序组件路径>", "admin": "<后台组件路径>"}`；路径相对各自 `components/` |
| `supported_platforms` | string[] | 是 | `["mp","admin"]` 的子集；未列出的平台不得下发 |
| `supported_exports` | string[] | 是 | `["png","pdf","xlsx","csv","json"]` 的子集；导出器按此裁剪 |
| `actions_schema` | object/null | 否 | 组件可发出的动作类型与参数约束；无交互为 `null` |
| `fallback_key` | string | 是 | 降级组件 key 或原语 id；不得等于自身；链深 ≤2 |
| `status` | enum | 是 | `draft` / `active` / `deprecated` / `disabled` |
| `client_min_version` | string | 是 | 支持该组件的最低客户端版本；低于此版本不下发，走 fallback |
| `registry_version` | string | 是 | 该 manifest 所属注册表快照版本（服务端写入，不由作者填） |
| `created_at` / `updated_at` | string | 是 | ISO 8601，服务端写入 |

### 2.1 状态语义

| status | 可被新答案选择 | 可渲染历史快照 | 说明 |
|---|---|---|---|
| `draft` | 否 | 否 | 开发中，仅后台预览可见 |
| `active` | 是 | 是 | 正常使用 |
| `deprecated` | 否 | 是 | 不再选新，历史仍可渲染；进入弃用窗口 |
| `disabled` | 否 | 否 | 紧急关闭；历史快照走 `fallback_key` |

### 2.2 分类与平台

- `metric`：指标卡/指标网格；两端均支持。
- `text`：正文、摘要、提示、分析判断（由 `variant` 区分）；两端均支持。
- `chart`：柱/条/折线/饼；小程序用 echarts-for-weixin，后台用 ECharts。
- `table` / `ranking` / `comparison`：表格与排名/对比。
- `source` / `action`：来源卡与动作行。
- `composite`：组合块（如汇报卡），仅用于导出与后台预览，11.12 小程序不渲染。

## 3. Manifest 示例：`ranking_bar`

```json
{
  "key": "ranking_bar",
  "version": "1.0.0",
  "name": "排名条形图",
  "category": "ranking",
  "description": "同一指标、同一层级、同一期的区域排名，条形长度表示数值大小。",
  "when_to_use": "用户问哪个区域最高、最低或前 N，且指标为数值型、同层级有效值不少于 3 个。",
  "props_schema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": false,
    "required": ["title", "unit", "period", "order", "items"],
    "properties": {
      "title": {"type": "string", "maxLength": 60},
      "unit": {"type": "string", "maxLength": 16},
      "period": {"type": "string", "pattern": "^[0-9]{4}$"},
      "order": {"type": "string", "enum": ["asc", "desc"]},
      "include_development_zones": {"type": "boolean", "default": false},
      "truncated": {"type": "boolean", "default": false},
      "items": {
        "type": "array",
        "minItems": 1,
        "maxItems": 15,
        "items": {
          "type": "object",
          "additionalProperties": false,
          "required": ["rank", "region_code", "region_name", "value"],
          "properties": {
            "rank": {"type": "integer", "minimum": 1},
            "region_code": {"type": "string", "maxLength": 64},
            "region_name": {"type": "string", "maxLength": 128},
            "value": {"type": "number"},
            "citation_id": {"type": "string", "maxLength": 32}
          }
        }
      }
    }
  },
  "data_requirements": {
    "value_type": "number",
    "levels": ["district", "town", "village"],
    "same_period": true,
    "min_valid_items": 3,
    "max_items": 15,
    "exclude_null": true
  },
  "example_props": {
    "title": "2025 年镇街常住人口（前 5）",
    "unit": "人",
    "period": "2025",
    "order": "desc",
    "include_development_zones": false,
    "items": [
      {"rank": 1, "region_code": "JD-QX", "region_name": "曲溪街道", "value": 185000, "citation_id": "c1"},
      {"rank": 2, "region_code": "JD-YL", "region_name": "云路镇", "value": 142000, "citation_id": "c1"}
    ]
  },
  "renderer": {
    "mp": "components/ranking-bar/index",
    "admin": "components/charts/RankingBar.vue"
  },
  "supported_platforms": ["mp", "admin"],
  "supported_exports": ["png", "pdf", "xlsx", "csv"],
  "actions_schema": {
    "allowed": ["drilldown", "export", "ask"],
    "drilldown": {"page": ["MP04"], "params": ["indicator_code", "period", "region_code"]}
  },
  "fallback_key": "data_table",
  "status": "active",
  "client_min_version": "1.0.0",
  "registry_version": "1.0.0",
  "created_at": "2026-11-10T09:00:00+08:00",
  "updated_at": "2026-11-10T09:00:00+08:00"
}
```

示例数值仅用于结构说明，不是真实统计。

## 4. 11.12 静态组件集

小程序与后台各自内置下表组件；注册表只负责选择与传参。P1 组件可先不发，或发布但默认 `disabled`。

| key | 名称 | 分类 | 平台 | 优先级 | 用途 | fallback | 导出 |
|---|---|---|---|---|---|---|---|
| `metric_card` | 指标卡 | metric | mp/admin | P0 | 单值 + 单位 + 期 + 来源 | `text` | png/pdf/xlsx |
| `metric_grid` | 指标网格 | metric | mp/admin | P0 | 2–6 个关键指标 | `data_table` | png/pdf/xlsx/csv |
| `text_profile` | 区域画像 | text | mp/admin | P0 | 简介/特色 + 关键指标 | `text` | png/pdf |
| `data_table` | 数据表 | table | mp/admin | P0 | 通用表格、最终兜底 | `text` | png/pdf/xlsx/csv |
| `bar_chart` | 柱/条形图 | chart | mp/admin | P0 | 单指标、多区域/多类别 | `data_table` | png/pdf/xlsx |
| `ranking_bar` | 排名条形图 | ranking | mp/admin | P0 | 同一指标排名 | `data_table` | png/pdf/xlsx/csv |
| `comparison_board` | 对比板 | comparison | mp/admin | P1 | 2–6 区域同指标对比 | `data_table` | png/pdf/xlsx |
| `pie_chart` | 饼图 | chart | mp/admin | P1 | 占比（≤8 类、全集完整） | `bar_chart` | png/pdf |
| `line_chart` | 折线图 | chart | mp/admin | P1 | ≥2 期趋势（M1 数据到位后） | `data_table` | png/pdf |
| `source_card` | 来源卡 | source | mp/admin | P0 | 引用、口径、数据时效 | `text` | png/pdf/xlsx |
| `action_row` | 动作行 | action | mp/admin | P0 | 下钻/对比/导出/追问 | 无（可不渲染） | png/pdf |
| `report_card` | 汇报卡 | composite | admin | P1 | 导出用组合版式（标题+指标+图+来源） | `text` | png/pdf |

补充约定：

1. `data_table` 是全局最终兜底；它本身必须有 `text` 兜底，避免表格数据非法时白屏。
2. `report_card` 只用于导出与后台预览；小程序端不注册，`supported_platforms` 仅 `admin`。
3. `line_chart` / `pie_chart` / `comparison_board` 在 11.12 可发布但 `status=disabled`，历史与评测不依赖它们。
4. 小程序 `app.json` 的 `usingComponents` 静态声明全部组件；后台在 `main.ts` 全局注册。均不使用动态 `import()`。

## 5. 通用 schema 渲染器原语

渲染器是"白名单解释器"，不是通用模板引擎。它只认识 8 个原语，其余全部映射到静态组件。

| 原语 | 输入 | 运行时可变（无需发版） | 必须发版 |
|---|---|---|---|
| `page` | `title`、`sections[]`、`meta` | 标题、区块顺序、区块显隐 | 版式规则、页眉页脚结构 |
| `section` | `heading?`、`children[]`、`collapsible?` | 标题、子块顺序 | 嵌套深度 >2、新容器语义 |
| `grid` | `columns`（1–4）、`gap`（预设）、`children[]` | 列数（预设内）、顺序、显隐 | 任意像素布局、瀑布流、绝对定位 |
| `text` | `variant`（body/summary/insight/notice/clarify）、`paragraphs[]`、`highlights?[]` | 文案、段落数、加粗片段 | 新 variant、富文本 HTML、图片混排 |
| `metric` | `label`、`value|null`、`unit`、`delta?`、`status?`、`citation_id?` | 数值、单位、标签、空值态 | 新状态枚举、新图标语义 |
| `table` | `columns[]`、`rows[][]`、`align?`、`unit?`、`truncated?` | 列名、行数据、列顺序、空值 | 合并单元格、公式、条件格式、可编辑 |
| `chart` | `chart_type`（bar/hbar/line/pie）、`categories[]`、`series[]`、`unit`、`sort?` | 数据、标题、排序、类别数（上限内） | 新图表类型、透传 ECharts option、双轴/标注线 |
| `action` | `actions[{type,label,target,permission?}]` | 按钮文案、目标参数、顺序 | 新动作类型、任意跳转 URL、脚本 |

### 5.1 可运行时变化 vs 必须发版

| 可运行时变化（改数据/配置即可） | 必须发版（改代码/提审） |
|---|---|
| props 数值、文案、单位、期 | 新增组件 key 或原语 |
| 区块顺序、显隐、列数（预设内） | props 语义变化（同一字段含义改变） |
| 表格列名与列顺序 | 新动作类型、新事件、新跳转协议 |
| 图表类型在已编译子集内切换 | 新图表类型、ECharts option 透传 |
| 主题 token 的既有取值（如强调色档位） | 新 token、新布局算法、新字体 |
| 启用/禁用组件 | 修改 `props_schema` 的必填项或类型 |

### 5.2 解析与降级顺序

```text
block.component
  → 快照 version（若客户端支持）
  → 该 key 的最新兼容 version
  → fallback_key
  → data_table
  → text（variant=notice）
```

任何一步失败：记录 `component_fallback` 事件（key、version、原因），不阻断整条答案。

## 6. AI 调用协议

### 6.1 调用链

```text
list_components(category?, platform?, intent?)
  → [{key, version, name, when_to_use, status, fallback_key}]
get_component(key, version?)
  → manifest（props_schema、data_requirements、limits、example_props）
render_component(key, version, props)
  → 服务端校验并生成 block（不是 LLM 工具）
validate(block)
  → schema + 引用 + 数值溯源 + 平台可用性
fallback(block)
  → fallback_key → data_table → text(notice)
```

说明：

1. 这四步都在**服务端内部**完成；LLM 只能触发 `list_components` 与 `get_component` 的语义（实现上可合并为一次"组件目录"注入），不能调用 `render_component`。
2. `render_component` 是组装步骤，不执行前端代码；它只做 schema 校验并写入 `component`/`version`。
3. 组件目录属于服务端只读能力，不计入 24 §6.2 的 5 次数据工具预算；仍受总超时约束。

### 6.2 Token 控制

| 措施 | 规则 |
|---|---|
| 目录体积 | `list_components` 最多返回 10 个 key，且每条只含 key、name、when_to_use |
| Schema 下发 | 每个请求最多拉取 2 个 manifest；按 `(key,version)` 进程内缓存 10 分钟 |
| 不内联全量 schema | system prompt 只放"key + 一行用途"，不放 JSON Schema |
| 示例裁剪 | `example_props` 最多 2 条 item，避免长上下文 |
| 重试 | 校验失败重试不复述整个 schema，只回传错误路径与允许值 |

### 6.3 意图到组件的确定性映射

规则层或兜底时使用下表，不依赖模型（与 24 §4.3 一致）：

| intent | 默认组件 | 条件不满足时 |
|---|---|---|
| `lookup` | `metric_card`（多指标用 `metric_grid`） | `text` |
| `rank` | `ranking_bar` | `data_table` |
| `compare` | `comparison_board`（P1） | `data_table` |
| `trend` | `line_chart`（P1） | `metric_grid` + `notice` |
| `composition` | `pie_chart`（P1） | `ranking_bar` |
| `profile` | `text_profile` + `metric_grid` | `text` |
| `relationship` | 无（M1） | `notice`（refused） |
| `export` | `action_row` + `notice` | `text` |
| `clarify` | `text`（variant=clarify）+ `action_row` | `text` |
| `refuse` | `text`（variant=notice，level=refused） | `text` |

### 6.4 props 校验顺序

1. JSON Schema 类型/必填/枚举/上限（`additionalProperties=false`）。
2. 业务上限：表格行、图表类别、排名条数、指标个数。
3. 引用完整：`citation_id` 必须存在于 Envelope。
4. 数值溯源：props 数值必须能在工具结果中找到（按精度四舍五入）。
5. 平台可用：`supported_platforms` 含当前平台，`client_min_version` 满足。
6. 动作合法：`actions[].type` 在组件 `actions_schema.allowed` 内。

## 7. 动作与交互

### 7.1 动作对象

```json
{
  "type": "drilldown",
  "label": "查看指标",
  "target": {
    "page": "MP04",
    "params": {"indicator_code": "population_resident", "period": "2025", "region_code": "JD-QX"}
  },
  "requires_auth": false,
  "permission": null
}
```

### 7.2 动作白名单

| type | 语义 | 目标 | 关键参数 | 权限 | 11.12 |
|---|---|---|---|---|---|
| `drilldown` | 进入下钻页面 | MP03/MP04、AD03 | `region_code`、`indicator_code`、`period` | 浏览权限 | 提供 |
| `filter` | 在当前页筛选 | 当前列表/图表 | `level`、`indicator_code`、`period`、`region_codes` | 浏览权限 | 提供（基础） |
| `compare` | 发起对比 | MP04 对比态 | `indicator_code`、`region_codes[2..6]`、`period` | 浏览权限 | P1 |
| `export` | 导出当前答案 | `POST /exports` | `source_type`、`source_id`、`format` | 见 25 §5 | 提供 |
| `ask` | 以建议问题继续提问 | MP05/MP06 | `question`、`session_id` | 问答权限 | 提供 |
| `open_detail` | 打开指标/区域详情 | MP03/MP04 | `region_code`、`indicator_code` | 浏览权限 | 提供 |
| `share` | 分享答案或导出物 | 微信分享/复制链接 | `answer_id` 或 `export_id` | 见 25 §5.4 | 提供（小程序） |
| `cross_filter` | 多块联动筛选 | 答案内多块 | `field`、`values[]` | 浏览权限 | M1 |

### 7.3 动作总线

1. 小程序与后台各有一个单一入口：`utils/action-bus.ts`（MP）与 `composables/useActionBus.ts`（后台）。
2. 总线持有 `type -> handler` 的静态映射；**不存在**动态注册或 `eval`。
3. 未知 `type`：不执行、不跳转，记录日志并提示"暂不支持该操作"。
4. 参数先按白名单裁剪，再交给 handler；多余字段丢弃，缺失必填字段则禁用按钮。
5. `permission` 只作为界面提示；真正的权限校验在后端（导出、管理动作）。
6. 动作不得携带任意外部 URL；`page` 只允许页面枚举值。

### 7.4 状态恢复

- 动作必须携带足够参数，使目标页可独立重建（不依赖上一页内存对象）。
- 返回栈恢复筛选条件；答案内动作使用 `answer_id` 作为恢复键。
- 深链格式：`<page>?<params>`；参数做白名单与类型校验。
- 导出/分享使用 `export_id` 或 `answer_id`，不传本地文件路径。

### 7.5 未来联动

`cross_filter` 属 M1：多个块订阅同一筛选 store，只有声明过的字段可联动；不允许任意谓词或表达式。11.12 不实现，避免把筛选逻辑写进 props。

## 8. 版本与兼容

### 8.1 语义化版本

| 变更 | 版本位 | 示例 |
|---|---|---|
| 必填 props 增删、类型/含义变化、删除枚举值 | MAJOR | `1.2.0` → `2.0.0` |
| 新增可选 props、放宽上限、新增枚举值 | MINOR | `1.2.0` → `1.3.0` |
| 渲染修复、文案/样式修正、无契约变化 | PATCH | `1.2.0` → `1.2.1` |

规则：

1. 已发布版本**不可修改**；任何变更发新版本。
2. 同一 key 最多保留 3 个可渲染版本；更早版本只保证历史快照可读。
3. `fallback_key` 指向的组件版本必须 ≥ 引用方所需的最小版本，且链深 ≤2、无环。
4. `client_min_version` 只升不降；降低需评估旧客户端。

### 8.2 快照

答案与导出都保存组件快照：

```json
{
  "registry_version": "1.0.0",
  "blocks": [
    {"id": "b1", "component": "ranking_bar", "version": "1.0.0", "props": {}},
    {"id": "b2", "component": "source_card", "version": "1.0.0", "props": {}}
  ]
}
```

快照不可变；渲染时"快照版本优先"，不回退到最新版。快照中的版本不存在时依次走 `fallback_key` → `data_table` → `text`。

### 8.3 弃用

1. `status=deprecated` 后：不再被新答案选择，但仍可渲染历史。
2. 弃用窗口：至少 2 个客户端版本或 30 天，取较长者。
3. 移除条件：无活跃答案/导出引用该版本（查询 `chat_messages`、`export_jobs`），且完成一次全量快照巡检。
4. 紧急关闭：`status=disabled` 立即生效，历史快照走 fallback，并记录审计。

### 8.4 兼容矩阵（示意）

| 客户端版本 | `ranking_bar@1.0.0` | `ranking_bar@2.0.0` | 行为 |
|---|---|---|---|
| 1.0.0 | 支持 | 不支持 | 2.0 块走 fallback |
| 1.1.0 | 支持 | 支持 | 正常 |
| 0.9.0 | 不支持 | 不支持 | 全部 fallback，并提示升级 |

## 9. 管理端界面

### 9.1 功能清单

| 功能 | 说明 | 权限 |
|---|---|---|
| 列表 | key、名称、分类、版本、状态、平台、最近使用 | admin |
| 详情 | manifest 全文、字段说明、版本历史、兼容矩阵 | admin |
| 预览 | 用 `example_props` 渲染；可切换 mp/admin 版式 | admin |
| 测试 | 粘贴 props → 校验 → 渲染，显示错误路径 | admin |
| 启用/禁用 | 修改 `status`（`active`/`disabled`） | admin |
| 版本 | 查看/对比版本；新版本从仓库发布，不在界面编辑 schema | admin |
| 使用量 | 引用该 key/version 的答案数、导出数、fallback 次数 | admin |

### 9.2 11.12 范围

| 项 | 11.12 | 后续 |
|---|---|---|
| 列表/详情 | 只读 | 保留 |
| 预览 | 只读，使用 `example_props` | 支持切换示例 |
| 测试 | 不做 | M1 |
| 启用/禁用 | 不做（改配置需发版） | M1 |
| 编辑 manifest | 不做；manifest 随代码仓库发布 | 仍不做（避免运行时改契约） |
| 使用量 | 不做 | M1 |

管理端改动写入 `audit_logs`（`action=component.update`，含 before/after）。

## 10. 验收清单与示例

### 10.1 验收清单

- [ ] `key` 全局唯一、`snake_case`、发布后未改名。
- [ ] `version` 符合 semver，已发布版本未被修改。
- [ ] `props_schema` 为合法 JSON Schema，`additionalProperties=false`，声明数量上限。
- [ ] `example_props` 能通过 `props_schema`，且能实际渲染。
- [ ] `fallback_key` 存在、不等于自身、无环、链深 ≤2。
- [ ] `renderer` 在 `supported_platforms` 对应端已静态注册。
- [ ] `client_min_version` 与客户端能力一致。
- [ ] `supported_exports` 中每种格式都有渲染路径或明确裁剪规则。
- [ ] `actions_schema.allowed` 是 07 §7.2 的子集。
- [ ] `status=disabled` 时历史快照可 fallback 渲染。
- [ ] 快照往返：保存 → 重新加载 → 渲染结果一致。
- [ ] 无数据、空 props、超限数据三种异常均有可见降级。

### 10.2 示例：`metric_grid` props

```json
{
  "title": "曲溪街道关键指标（2025）",
  "columns": 2,
  "items": [
    {"label": "常住人口", "value": 185000, "unit": "人", "citation_id": "c1"},
    {"label": "区域面积", "value": 52.6, "unit": "平方公里", "citation_id": "c2"},
    {"label": "户籍人口数", "value": null, "unit": "人", "status": "no_data"}
  ]
}
```

空值显示"无数据"，不得显示 0。

### 10.3 示例：未知组件降级

```text
block.component = "map_choropleth"（11.12 未注册）
  → 注册表无此 key
  → fallback_key = "data_table" 不存在该块 fallback
  → 全局兜底 data_table（用 data_ref 生成表格）
  → data_table 失败 → text(notice, COMPONENT_UNAVAILABLE)
  → 记录 component_fallback，答案其余块正常展示
```

### 10.4 示例：禁用组件的历史快照

```text
快照 component = "pie_chart", version = "1.0.0"
注册表 status = disabled
  → 不渲染 pie_chart
  → fallback_key = "bar_chart"（若可用）
  → 否则 data_table
  → notice(level=warning, code=COMPONENT_DISABLED)
```

## 11. 开放问题

1. 组件注册表存数据库还是随代码发布的 JSON 文件？11.12 建议"仓库 JSON + 启动加载"，避免运行时编辑契约。
2. `report_card` 的版式参数（页眉、页脚、Logo 位）需要 UE 冻结后补 schema。
3. `line_chart` 需要多期数据；M1 数据到位前是否发布为 `disabled`，需与 11.12 演示脚本确认。
4. 小程序 Markdown/表格渲染能力需在 MP-001 阶段实测，必要时把 `text` 的渲染限定为纯段落。
5. 组件使用量统计需要额外的 `component_usage` 事件表，是否纳入 M1 待定。
