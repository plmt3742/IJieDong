# ADR-002: 数据模型

- 状态：Proposed（待 B-003 落地验证）
- 日期：2026-11-06
- 决策人：项目开发者
- 相关任务：DATA-001~008
- 相关文档：`docs/agent/05-architecture.md` §5、`docs/product/04-data-catalog.md`

## 1. 背景

原始 xls 是“区域 × 指标”的稀疏明细：

- 227 个区域（1 区 + 15 镇街 + 211 村居）。
- 15 个指标（2 文本 + 13 数值）。
- 仅 2025；数据值全空。
- 不同层级适用指标不同；经开区/生态城特殊；村居名称有别名问题。
- 未来可能增加年份、指标、区域；需要审计/追溯。

需要决定：用宽表、纯 EAV、JSON 文档，还是规范化的“区域/指标/数据值”模型。

## 2. 决策

采用**受控的规范化模型**：

```text
regions (区域树)
  ← region_aliases (导入别名)
indicators (指标元数据)
  ← data_values (区域 × 指标 × 年份 × 值)
      ← data_sources (来源)
      ← import_jobs (导入批次)
audit_logs (修改审计)
```

核心表：

- `regions`：`code`、`name`、`level`（district/town/village）、`category`（administrative/development_zone）、`parent_id`。
- `region_aliases`：处理“玉滘镇/玉窖镇”等名称不一致。
- `indicators`：`code`、`name`、`unit`、`value_type`（number/text）、`applicable_levels`。
- `data_values`：`region_id`、`indicator_id`、`period_year`、`period_type`、`value_number`、`value_text`、`status`、`source_id`；唯一键 `(region_id, indicator_id, period_year, period_type)`。
- `data_sources`、`import_jobs`、`audit_logs`。

规则：

- 空值 = `NULL`（无数据），不是 0。
- 文本指标只存 `value_text`；数值指标只存 `value_number`。
- 指标适用层级由 `applicable_levels` 控制；导入时校验。
- 不把指标名/区域名冗余进 `data_values`；显示时 join。
- 不用纯 EAV 无约束：指标有元数据/单位/类型/层级校验。

## 3. 后果

### 正面

- 新增指标/年份不需要改表结构。
- 稀疏数据（经开区/生态城/村居指标差异）自然表达。
- 指标口径/单位集中管理；历史数据可保留。
- 支持排名/对比/趋势查询；审计与来源可追溯。
- 区域树支持任意层级扩展。

### 负面/代价

- 查询需要 join；需要索引/视图/缓存。
- 指标/区域的显示名变更需要 join 或缓存。
- 导入需要更多校验/别名处理。
- 纯 SQL 分析不如宽表直观；可加视图/物化视图（P1）。

### 风险与缓解

| 风险 | 缓解 |
|---|---|
| 查询性能 | 索引 `(indicator_id, period_year)`、`(region_id, period_year)`；数据量小，足够 |
| 导入映射复杂 | 别名表 + 错误报告 + 测试 |
| 指标扩展导致元数据膨胀 | `indicators` 增加分类/排序/描述；P1 做管理界面 |
| 国产库不支持 JSON/部分类型 | `applicable_levels` 可用关联表替代；保持可移植 |

## 4. 备选方案

| 方案 | 优点 | 缺点 | 为什么没选 |
|---|---|---|---|
| 宽表（一行区域，15 列指标） | 查询简单；导出方便 | 加指标/年份要改表；稀疏数据大量 NULL；历史难 | 扩展性差 |
| 纯 EAV（entity-attribute-value） | 最灵活 | 无类型/单位/层级约束；查询复杂；易脏 | 政府数据需要治理 |
| JSON 文档（每个区域一个 JSON） | 灵活；读写简单 | 查询/排名/审计弱；模式漂移 | 不适合统计查询 |
| 图数据库 | 关系表达强 | 过重；团队/部署成本高 | 当前不需要 |
| 单独文本表 | 文本查询优化 | 增加表；当前文本少 | 不需要 |

## 5. 实施要点

1. Alembic 初始迁移包含所有表/索引/唯一约束。
2. `regions.code` 稳定；`external_code` 预留行政区划码。
3. `region_aliases` 先导入“玉窖镇→玉滘镇”；后续可加其他别名。
4. `data_values` 的 `value_type` 校验在服务层 + 数据库 CHECK/触发器（按数据库能力）。
5. 空值不写 0；导入空值给 `EMPTY_VALUE` 警告。
6. 排名/对比查询排除 NULL；文本指标不参与排名。
7. 为常用查询建视图（P1）：`v_town_indicator_values`、`v_region_profile`。
8. 审计：`audit_logs.detail` 存 before/after；不在 `data_values` 里做软删（用 status）。

## 6. 复审条件

- 指标数超过 100 或数据行超过 100 万 → 评估分区/物化视图/列存。
- 需要复杂的多指标交叉分析/自助 BI → 评估宽表/OLAP。
- 国产库不支持 JSON/CHECK → 改为关联表/应用层校验。
- 需要多版本数据/时间旅行 → 增加 `data_value_revisions`。
- 需要实时数据 → 评估流式/时序库。

## 7. 链接

- `docs/agent/05-architecture.md` §5
- `docs/product/04-data-catalog.md`
- `docs/agent/09-risks.md` R-006/R-012
