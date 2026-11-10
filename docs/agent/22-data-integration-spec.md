---
owner: 项目开发者
last_updated: 2026-11-10
status: draft
read_when: 准备/填写 Excel 模板前；实现导入器与数据校验前；对外沟通数据接口与更新流程时
---

# 22 · 数据接入与 API 契约（草案，待实现）

> 本文定义“数据提供方给什么、系统怎么校验、接口怎么调”。与 [21-technical-architecture-v2.md](21-technical-architecture-v2.md) 配套使用。
> 当前真实数据未提供；文中数值规则来自空白模板分析，不代表真实统计口径。B02 已实现确定性 `seed_demo.py` 与 227 区域 fixture；Excel 导入 API 与写接口尚未实现。

## 1. 数据提供方需要准备什么

| 交付物 | 内容 | 责任人 | 时点 |
|---|---|---|---|
| 填好的 Excel | 按第 3 节模板填写；一表一期；区域名称与第 5 节清单一致 | 数据提供方 | 首次导入前 |
| 区域清单确认 | 227 个区域是否为最新；是否有撤并/更名 | 数据提供方 | 首次导入前 |
| 指标口径说明 | 每个指标的定义、统计范围、单位、数据来源、责任科室 | 数据提供方 | 首次导入前 |
| 别名确认 | `玉窖镇` 与 `玉滘镇` 的规范写法 | 数据提供方 | 首次导入前 |
| 历史数据 | 是否存在 2020–2024 年数据 | 数据提供方 | M1 前 |
| 更新计划 | 年度/季度/不定期；每次更新范围 | 数据提供方 | 上线前 |
| 接口资料 | 若有上级平台接口：地址、鉴权、字段映射、频率 | 数据提供方 | 接口对接前 |

责任矩阵：

| 事项 | 数据提供方 | 项目开发 | 数据管理员 | 审批者 |
|---|---|---|---|---|
| 数据真实性与口径 | 负责 | 不判断 | 复核 | 知会 |
| 模板与校验规则 | 确认 | 实现 | 使用 | — |
| 导入执行 | 提供文件 | 提供工具 | 执行 | — |
| 异常数据处置 | 解释 | 提供报告 | 修正/重导 | 必要时审批 |
| 权限与账号 | 提供名单 | 批量建号 | 维护 | 审批申请 |
| 演示数据 | 知会 | 生成并标注 | 不得对外当真实数据 | — |

## 2. Excel 模板

### 2.1 v1 基础列（必须支持）

| 列 | 必填 | 规则 | 示例 |
|---|---|---|---|
| 区域类型 | 是 | 仅 `揭东区`、`镇街`、`村居` | 镇街 |
| 区域名称 | 是 | 区/镇街用规范名；村居用 `镇街-村居` | 玉湖镇-浮山村 |
| 数据名称 | 是 | 与指标字典中文名一致（允许前后空格） | 常住人口 |
| 数据期 | 是 | Demo v0 仅 `2025`；M1 起支持 `2025Q1` 等 | 2025 |
| 单位 | 是 | 与指标单位一致 | 人 |
| 数据值 | 否 | 数值或文本；空表示无数据 | 12345 |

### 2.2 v2 可选列（同一导入器兼容）

| 列 | 必填 | 规则 |
|---|---|---|
| 指标编码 | 否 | 填了则以编码为准；与 `数据名称` 冲突报错 |
| `维度:<键>` | 否 | 表头以 `维度:` 开头，如 `维度:性别`；值为维度取值 |
| 数据来源 | 否 | 来源名称；未填则用批次默认来源 |
| 质量状态 | 否 | `verified`/`provisional`/`estimated`/`missing`/`not_applicable`/`suppressed`；默认 `verified` |
| 备注 | 否 | 自由文本，仅入报告，不入观测值 |

兼容规则：

1. 有 `指标编码` 列且非空 → 按编码匹配；否则按 `数据名称` 精确匹配（trim 后）。
2. 未知列：以 `维度:` 开头按维度处理，其余给 `COLUMN_UNKNOWN` 警告并忽略。
3. v1 文件不含维度 → 维度 hash 取常量；与 v2 数据可共存。
4. 维度键必须已在指标上注册，否则 `DIMENSION_INVALID`。

示例（v2）：

| 区域类型 | 区域名称 | 指标编码 | 数据名称 | 数据期 | 单位 | 数据值 | 维度:性别 | 质量状态 |
|---|---|---|---|---|---|---|---|---|
| 镇街 | 曲溪街道 | population_resident | 常住人口 | 2025 | 人 | 86000 | total | verified |
| 镇街 | 曲溪街道 | population_resident | 常住人口 | 2025 | 人 | 44200 | male | provisional |

## 3. 指标数据字典（15 项）

| 编码 | 中文名 | 单位 | 值类型 | 适用层级/类别 | 聚合 | 精度 | 备注 |
|---|---|---|---|---|---|---|---|
| `region_intro` | 地区简介 | 文本 | long_text | 区/全部镇街/村居 | 不汇总 | ≤150 字 | 不进数值图表 |
| `region_feature` | 地区特色 | 文本 | long_text | 区/全部镇街/村居 | 不汇总 | ≤300 字 | 不进数值图表 |
| `area` | 区域面积 | 平方公里 | decimal | 区/全部镇街/村居 | 不自动汇总 | 2 位小数 | 各级已给值，不自动加总 |
| `admin_village_count` | 行政村数量 | 个 | integer | 区/13 个行政镇街 | 可作一致性校验 | 整数 | 2 个开发区/生态城不适用 |
| `population_resident` | 常住人口 | 人 | integer | 区/全部镇街/村居 | 可作一致性校验 | 整数 | 空值不等于 0 |
| `population_household` | 户籍人口数 | 人 | integer | 区/全部镇街/村居 | 可作一致性校验 | 整数 | 空值不等于 0 |
| `farmland_area` | 耕地面积 | 亩 | decimal | 区/13 个行政镇街/村居 | 可作一致性校验 | 2 位小数 | 2 个开发区/生态城不适用 |
| `forest_area` | 林地面积 | 亩 | decimal | 区/13 个行政镇街/村居 | 可作一致性校验 | 2 位小数 | 2 个开发区/生态城不适用 |
| `gdp` | 地区生产总值 | 亿元 | currency | 区/2 个开发区、生态城 | 不自动汇总 | 2 位小数 | 模板仅 3 行（区 + 2 开发区）；13 个行政镇街无值；GDP 排名非必需 |
| `budget_revenue` | 地方一般公共预算收入 | 亿元 | currency | 仅区 | 不汇总 | 2 位小数 | 镇街/村居不适用 |
| `budget_expenditure` | 地方一般公共预算支出 | 亿元 | currency | 仅区 | 不汇总 | 2 位小数 | 同上 |
| `import_export_total` | 进出口总额 | 亿元 | currency | 仅区 | 不汇总 | 2 位小数 | 同上 |
| `fixed_asset_investment` | 固定资产投资 | 亿元 | currency | 仅区 | 不汇总 | 2 位小数 | 同上 |
| `industrial_investment` | 工业投资额 | 亿元 | currency | 仅区 | 不汇总 | 2 位小数 | 同上 |
| `retail_total` | 社会消费品零售总额 | 亿元 | currency | 仅区 | 不汇总 | 2 位小数 | 同上 |

模板事实校验：

| 层级 | 指标数 | 区域数 | 行数 |
|---|---:|---:|---:|
| 揭东区 | 15 | 1 | 15 |
| 13 个行政镇街 | 8 | 13 | 104 |
| 2 个开发区/生态城 | 6 | 2 | 12 |
| 村居 | 7 | 211 | 1477 |
| 合计 | — | 227 | 1608 |

镇街层面指标并集为 9 项（8 + `gdp`）。`gdp` 仅区级与 2 个开发区/生态城有值，因此**镇街 GDP 排名不作为 Demo v0 验收项**；排名接口须能正确处理“部分区域无值”，不补零、不参与排序。

## 4. 区域结构（227 个）

| 层级 | 数量 | 编码示例 | 说明 |
|---|---:|---|---|
| 区 | 1 | `JD` | 根节点，父级为空 |
| 镇街（行政） | 13 | `JD-T-01` … `JD-T-13` | 曲溪、云路、玉滘、玉湖、新亨、锡场、埔田、磐东、月城、霖磐、桂岭、龙尾、白塔 |
| 镇街（开发区/生态城） | 2 | `JD-Z-01`、`JD-Z-02` | 揭东经济开发区、揭东中德金属生态城；`category=development_zone` |
| 村居 | 211 | `JD-V-001` … `JD-V-211` | 格式 `镇街-村居`，按第一个 `-` 拆父级 |
| **合计** | **227** | — | 开发区/生态城无村居 |

- 村居前缀存在 `玉窖镇` 与 `玉滘镇` 不一致；统一以 `玉滘镇` 为规范名，导入时经 `region_aliases` 映射，禁止模糊匹配或静默纠正。
- 村居类型（村/社区）模板未单列，展示可按后缀推断；如需精确分类，M1 增加 `village_type`。
- `external_code` 预留给行政区划码/统计用区划代码，当前为空，取值规则待需求方确认。
- 区/镇街/村居名称均为显示名；历史数据只引用 `regions.id`，改名不影响历史。

## 5. 校验规则与错误码

| 阶段 | 规则 | 级别 | 错误码 |
|---|---|---|---|
| 文件 | 扩展名 `.xls`/`.xlsx`；≤10MB；≤5000 行 | 错误 | `IMPORT_TOO_LARGE` / `IMPORT_ROW_LIMIT` |
| 表头 | v1 六列齐全；列名 trim 后匹配 | 错误 | `HEADER_MISSING` |
| 表头 | 非 `维度:` 的未知列 | 警告 | `COLUMN_UNKNOWN` |
| 区域 | `区域类型 + 区域名称` 能定位唯一区域（含别名） | 错误 | `REGION_NOT_FOUND` |
| 区域 | 同名/多义 | 错误 | `REGION_AMBIGUOUS` |
| 区域 | 村居前缀父级存在且为镇街 | 错误 | `REGION_PARENT_NOT_FOUND` |
| 区域 | 区域类型与 `regions.level` 一致 | 错误 | `REGION_LEVEL_MISMATCH` |
| 指标 | `数据名称` 或 `指标编码` 存在 | 错误 | `INDICATOR_NOT_FOUND` / `INDICATOR_CODE_UNKNOWN` |
| 指标 | 名称与编码同时给出且不一致 | 错误 | `INDICATOR_NAME_CODE_MISMATCH` |
| 指标 | 指标适用于该区域层级/类别 | 错误 | `INDICATOR_NOT_APPLICABLE` |
| 单位 | 与指标 `unit_code` 一致 | 错误 | `UNIT_MISMATCH` |
| 数值 | 去千分位后可解析；整数型不得带小数 | 错误 | `VALUE_TYPE_INVALID` / `NUMBER_FORMAT_INVALID` |
| 数值 | 超出合理范围（如负数人口） | 警告 | `VALUE_OUT_OF_RANGE` |
| 文本 | 长度不超过指标 `max_length` | 错误 | `TEXT_TOO_LONG` |
| 维度 | 键已注册、值在域内 | 错误 | `DIMENSION_INVALID` |
| 数据期 | 格式合法且在允许范围内 | 错误 | `PERIOD_INVALID` |
| 重复 | 文件内 `(区域, 指标, 数据期, 维度)` 不重复 | 错误 | `DUPLICATE_ROW` |
| 质量 | `质量状态` 在枚举内 | 错误 | `QUALITY_STATUS_INVALID` |
| 来源 | `数据来源` 已存在，否则按批次来源 | 警告 | `SOURCE_UNKNOWN` |
| 空值 | `数据值` 为空 | 警告 | `EMPTY_VALUE` |
| 数据缺失 | 模板未提供但指标适用（如镇街 GDP） | 提示 | `MISSING_DATA_INFO` |

级别含义：错误导致该行失败（atomic 模式下整批不写）；警告与提示不阻塞，但写入报告。

`INDICATOR_NOT_APPLICABLE` 只用于指标确实不适用（如开发区/村居的行政村数量）；模板未提供但指标适用属于数据缺失，使用 `MISSING_DATA_INFO`，不得写成 not_applicable。

## 6. 导入批次、报告、回滚与审计

```text
上传 → 创建 import_jobs(pending) → 解析/校验(running)
     → atomic：全部通过才写；partial：逐行写
     → 统计 success/error 行 → 写 observations + audit_logs
     → 生成报告 → 状态 success/partial/failed
```

- 状态：`pending`、`running`、`success`、`partial`、`failed`。
- 报告字段：`row_number`、`region_name`、`indicator_name`、`column`、`code`、`message`、`suggestion`。

```json
{
  "job_id": 42,
  "status": "partial",
  "mode": "partial",
  "total_rows": 1608,
  "success_rows": 1600,
  "error_rows": 8,
  "errors": [
    {
      "row_number": 18,
      "region_name": "玉窖镇-饶美村",
      "indicator_name": "区域面积",
      "column": "单位",
      "code": "UNIT_MISMATCH",
      "message": "指标“区域面积”的单位应为“平方公里”，实际为“亩”",
      "suggestion": "检查模板列或指标选择"
    }
  ]
}
```

- 写入按唯一键 upsert：`version + 1`，记录 `updated_by`、`updated_at`、`import_job_id`。
- 回滚：Demo v0 不提供自动回滚，修正后重新导入产生新批次；M1 增加 `revert_of_job_id`，按批次反向恢复 before 值前先做快照。
- 审计：批次创建、提交、失败、回滚，以及单条手工修改都写 `audit_logs`，含 before/after 与 `request_id`。
- 同一文件重复导入不报错，但会生成新批次并递增版本；报告需提示“本次覆盖 N 条”。

## 7. API 集成

### 7.1 认证

- 内部后台：`Authorization: Bearer <JWT>`，角色 `editor`/`admin`。
- 外部系统推送：服务账号 JWT 或 API Key，**方式待定**；无论哪种都必须绑定来源并限流。
- 所有写接口要求 HTTPS；不接受仅靠来源 IP 的信任。

### 7.2 端点

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/admin/imports` | 上传文件；`multipart/form-data`，字段 `file`、`mode`、`source_id` |
| GET | `/api/v1/admin/imports` | 批次列表，分页 |
| GET | `/api/v1/admin/imports/{id}` | 批次状态与统计 |
| GET | `/api/v1/admin/imports/{id}/errors` | 错误报告（JSON 或 CSV） |
| POST | `/api/v1/admin/imports/{id}/revert` | 回滚（M1） |
| GET | `/api/v1/data-values` | 查询观测值，支持 `region_id`、`indicator_code`、`period_year`、`quality_status`；Demo v0 使用 `period_year`，M1 改 `period_key` |
| POST | `/api/v1/admin/data-values` | 单条新增 |
| PATCH | `/api/v1/admin/data-values/{id}` | 单条修改 |

> Demo v0 已实现 `POST /api/v1/admin/imports`、批次列表/详情/错误报告和只读 `GET /api/v1/data-values`；`/admin/data-values` 单条写接口属于 BE-005，当前返回 404。

创建批次响应：

```json
{
  "data": {
    "job_id": 42,
    "status": "running",
    "mode": "atomic",
    "total_rows": 0,
    "success_rows": 0,
    "error_rows": 0
  },
  "meta": {"request_id": "req_01H..."}
}
```

查询响应：

```json
{
  "data": [
    {
      "region_code": "JD-T-01",
      "region_name": "曲溪街道",
      "indicator_code": "population_resident",
      "period_key": "2025",
      "value": 86000,
      "unit": "人",
      "quality_status": "verified",
      "version": 3,
      "source": "2025 年统计报表"
    }
  ],
  "meta": {
    "request_id": "req_01H...",
    "page": 1,
    "page_size": 20,
    "total": 1,
    "has_next": false,
    "data_version": "2025.3",
    "warnings": []
  }
}
```

### 7.3 分页、限流、幂等与错误处理

- 分页：`page`（默认 1）、`page_size`（默认 20，最大 100）；返回 `meta.total`、`meta.has_next`。
- 限流：导入 5 次/小时/账号；手工写 120 次/小时；查询 600 次/小时。超限返回 429 与 `Retry-After`。
- 幂等：所有 POST/PATCH 支持 `Idempotency-Key`，窗口 24 小时；同键不同请求体返回 `IDEMPOTENCY_CONFLICT`。
- 重试：仅对 429、500、502、503、504 重试，指数退避（1s/2s/4s，最多 3 次）；4xx 不重试。
- 错误响应统一 `{error:{code,message,details}, request_id}`；客户端应记录 `request_id` 便于排查。
- 版本冲突：修改时携带 `If-Match: <version>`，不一致返回 `DATA_VERSION_CONFLICT`。

## 8. 数据更新、版本与演示数据

| 项 | 规则 |
|---|---|
| 版本 | 每条观测值有 `version`；`meta.data_version` 为本次发布批次标识 |
| 更新 | 同一唯一键覆盖写并递增版本；历史 before/after 进审计 |
| 周期 | 年度为默认；季度/月度待需求方确认后启用 |
| 责任 | 数据提供方出数，数据管理员执行导入，审批者按需审批 |
| 真实数据 | 到位后按 v1/v2 模板导入，不改表结构与接口 |

合成演示数据规则：

1. 生成脚本固定随机种子，输出可复现；脚本路径 `services/api/scripts/seed_demo.py`。
2. 来源记为 `source_type=demo`、名称含“演示数据（合成）”，不得写入真实来源。
3. 界面对演示数据加显著标识；导出文件与图表带“演示数据”水印。
4. AI 回答命中演示数据时追加 `notice`；不得表述为真实统计。
5. 真实数据导入前，演示数据可被同唯一键覆盖；导入器需在报告中明确“覆盖演示数据 N 条”。
6. 对外演示材料必须同时标注“演示数据”，不得单独截图对外发布。

## 9. 验收清单

- [ ] v1 模板 1608 行可完整导入，无阻塞性错误。
- [ ] v2 模板含 `指标编码` 与维度列时可导入，v1 文件不受影响。
- [ ] `玉窖镇` 村居可正确挂到 `玉滘镇`，报告无静默纠正。
- [ ] 2 个开发区/生态城的 6 项指标导入成功，不因缺村居/耕地/林地报错。
- [ ] `gdp` 仅 3 行入库；排名接口对缺失区域不补零、不参与排序。
- [ ] 空值产生 `EMPTY_VALUE` 警告且不入库为 0。
- [ ] 重复行、单位错误、超长文本、非法数据期均能定位到行与列。
- [ ] atomic 模式任一行失败时整批不写；partial 模式写入通过行。
- [ ] 同文件重复导入产生新批次并递增版本，审计含 before/after。
- [ ] 手工修改与导入均写审计，且可按 `request_id` 追溯。
- [ ] 演示数据在界面、导出、AI 回答三处均有标识。
- [ ] 分页、限流、幂等键、版本冲突按契约返回。

## 10. 常见问题

**Q1：数据值为空要不要填 0？**
不要。空值表示“无数据”，系统存 NULL；填 0 会被当作真实数值参与统计与图表。

**Q2：所有镇街都要填全部 15 个指标吗？**
不需要。按第 3 节“适用层级/类别”填写；不适用的格子留空即可，系统给提示而非错误。

**Q3：GDP 只有区和两个开发区有，镇街排名怎么办？**
排名接口只对有值的区域排序，并在结果中标注缺失；Demo v0 不把 GDP 镇街排名作为验收项。

**Q4：村居前缀写“玉窖镇”会被拒绝吗？**
不会。别名表会映射到 `玉滘镇`，但报告中会记录使用了别名，便于后续统一模板。

**Q5：可以一次上传多个年份吗？**
Demo v0 只接受 `2025`；M1 支持同一文件多期，但仍要求每行 `数据期` 合法。

**Q6：导入后发现错了怎么办？**
Demo v0 修正文件后重新导入，系统按唯一键覆盖并保留审计；M1 提供按批次回滚。

**Q7：外部系统能否直接写库？**
不能。只允许通过受控 API 写入，复用同一套校验、审计与限流。
