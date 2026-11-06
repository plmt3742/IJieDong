# packages/chart-spec · 图表契约与渲染

> 状态：占位（B-002/B-006 创建）。

## 职责

- 定义 `ChartSpec` 类型/JSON Schema。
- 提供 `ChartSpec → ECharts option` 适配。
- 后台/H5/小程序共用渲染规则（类型、颜色、单位、空值、排序）。

## 计划

```text
src/
├── types.ts        # ChartSpec 类型
├── schema.ts       # JSON Schema/校验
├── to-echarts.ts   # ChartSpec → ECharts option
├── theme.ts        # 政府风格主题
└── index.ts
```

## ChartSpec 规则

- 类型：`bar` / `hbar` / `line` / `pie` / `table`。
- 数值指标才允许图表；文本指标只表格/卡片。
- `null` 表示无数据；渲染跳过并标注，不画 0。
- 饼图类别过多合并“其他”；条形图限制条目数。
- 小程序端控制数据量/动画，避免卡顿。

## 边界

- 不做数据查询/API 调用。
- 不渲染任意 JS/HTML。
- 不把 ECharts option 存进数据库；数据库只存 ChartSpec。

## 下一步

1. 与 AI-001 一起定义 schema。
2. 实现柱/条/饼/表；折线待多年数据。
3. 后台/H5 先用，小程序 spike 后接入。
