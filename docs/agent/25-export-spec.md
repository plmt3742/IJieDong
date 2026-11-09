---
owner: 项目开发者
last_updated: 2026-11-10
status: draft
read_when: 实现或评审导出接口、导出按钮、权限、文件存储与清理前
---

# 25 · 导出规范（草案）

> 状态：**契约草案，待实现**。本文承接 [05-architecture.md](05-architecture.md) §6/§9 与 [24 AI 与 AnswerBlocks 契约](24-ai-and-component-spec.md)，组件的导出能力见 [07 组件库规范](../product/07-component-library-spec.md) §2/§4。
> 已确认决策：支持 PNG / PDF / XLSX / CSV，**不设默认或预选格式**，每次由用户选择；**游客不能导出**，已批准角色按权限导出；导出使用答案快照，不重新提问、不重新取数；导出内容包含引用、数据时效、生成时间与水印；不单独设"领导模式"。
> 文中 JSON 数值与文件大小为结构示例，不是真实统计或实测结果。

## 1. 目标、范围、非目标

### 1.1 目标

1. 用一份契约统一"导出什么、从哪来、谁能导、怎么渲染、怎么清理"。
2. 保证导出**可复现**：同一答案快照在不同时间导出，内容一致；数据后续变更不影响历史导出。
3. 保证导出**可追溯**：包含指标、区域、期、来源、数据时效、生成时间、引用与水印。
4. 保证导出**可控**：权限在服务端判定，游客与未批准申请者一律拒绝。
5. 给出各格式的渲染路径、资源上限、清理策略与验收矩阵。

### 1.2 范围

- 11.12 Demo v0 的答案导出（小程序与后台）。
- 格式：PNG、PDF、XLSX、CSV；JSON 为可选机器可读格式（P1）。
- `export_jobs` 数据模型、`POST /exports`、`GET /exports/{id}`、下载链接。
- 服务端渲染、字体、存储、清理、审计与测试矩阵。

### 1.3 非目标

- 不做定时导出、批量导出、邮件/短信推送、导出订阅。
- 不做 BI 工作簿（透视表、公式、联动图表）与可编辑报表。
- 不做游客导出，不做匿名公开下载链接。
- 不以"小程序截图"代替导出；截图不含引用、时效与水印，不作为交付物。
- 不做 M1 的地图、时序动画导出。

## 2. 格式

### 2.1 格式清单

| 格式 | MIME | 扩展名 | 渲染路径 | 内容形态 | 上限 | 11.12 |
|---|---|---|---|---|---:|---|
| PNG | `image/png` | `.png` | 服务端 Chromium 渲染静态 HTML 后截图（2x） | 单页汇报卡，长图按块纵向拼接 | 3 MB | 提供 |
| PDF | `application/pdf` | `.pdf` | 服务端 Chromium 打印，A4 纵向，1–2 页 | 标题、块、来源、页脚、水印 | 10 MB | 提供 |
| XLSX | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | `.xlsx` | `openpyxl` | 3 个工作表：答案摘要、数据、引用 | 10 MB | 提供 |
| CSV | `text/csv; charset=utf-8` | `.csv` | Python 标准库 `csv` | 单表：表头 + 数据行，UTF-8 BOM | 5 MB | 提供（仅单表答案） |
| JSON | `application/json` | `.json` | 直接序列化快照 | AnswerEnvelope 快照 + 导出元数据 | 10 MB | 可选（P1） |

### 2.2 不设默认格式

1. 请求必须显式携带 `format`；缺失返回 `EXPORT_FORMAT_REQUIRED`（422），**不得**由服务端补默认值。
2. 客户端格式选择器初始为"未选择"；确认按钮在未选择时禁用；不得用上次选择预选。
3. 可以显示"上次使用 PDF"之类的文字提示，但不得勾选或预选。
4. 即使答案只有一种可渲染形态，也必须让用户显式选择；不可渲染的格式应置灰并说明原因，而不是自动切换。
5. 导出任务记录用户实际选择的格式；切换格式需新建任务，不复用同名文件。

### 2.3 格式适用性

| 答案内容 | PNG | PDF | XLSX | CSV |
|---|---|---|---|---|
| 纯文本/提示 | 支持 | 支持 | 摘要页 | 不支持（无表格） |
| 指标卡/指标网格 | 支持 | 支持 | 数据页 | 支持（转两列表） |
| 图表 | 支持 | 支持 | 数据页（值表） | 不支持 |
| 表格 | 支持 | 支持 | 数据页 | 支持（仅第一张表） |
| 排名 | 支持 | 支持 | 数据页 | 支持 |
| 多表格 | 支持 | 支持 | 多区块同一工作表 | 不支持（422 `EXPORT_FORMAT_UNSUPPORTED`） |

CSV 规则：只导出**第一张表**或排名块转成的两列表；不含合并单元格、不含颜色、不含公式；标题、单位、期、来源写入表头与文件名，完整元数据见 XLSX 摘要页或 JSON。

## 3. 导出内容

### 3.1 必备内容

| 项 | 说明 | PNG/PDF | XLSX | CSV |
|---|---|---|---|---|
| 标题 | 答案标题，或"指标 + 区域 + 期"自动生成 | 页首 | 摘要页 A1 | 文件名 + 表头 |
| 块 | 快照中的块，按顺序渲染；不支持的组件走 fallback | 是 | 数据页 | 表格/排名/指标类（转表） |
| 关键数字 | 只来自块 props，不重新计算 | 是 | 是 | 是 |
| 指标/区域/期 | 每个块或表头标注 | 是 | 表头 + 摘要页 | 表头 |
| 来源 | `source_card` 与引用列表 | 是 | 引用页 | 表头"来源"列/文件名 |
| 数据时效 | `data_as_of` | 页脚 | 摘要页 | 表头 |
| 生成时间 | `generated_at`（ISO 8601，+08:00） | 页脚 | 摘要页 | 文件名 |
| 水印 | 显示名 + 时间 + "内部资料" | 每页 | 页眉/首行说明 | 不加水印（表头标注导出人） |
| 引用 | 指标、区域、期、来源 | 末页/页脚 | 引用页 | 表头 |
| 导出编号 | `export_id` | 页脚 | 摘要页 | 文件名 |

### 3.2 不导出

- 系统提示、模型名以外的内部参数、工具调用原始报文、token 用量明细。
- 用户 openid、手机号、密码哈希、JWT、任何密钥。
- 未在快照中的实时数据；导出过程**禁止**回查数据库补数。
- 演示数据必须保留"演示数据"标识，不得在导出时去除。

### 3.3 标题生成规则

1. 优先用用户指定标题（≤60 字）。
2. 否则用答案首块标题。
3. 再否则用 `指标 + 区域范围 + 期`，例如"2025 年镇街常住人口排名"。
4. 标题不得包含 HTML、换行、文件名非法字符（`\ / : * ? " < > |`）。

## 4. 快照模型

### 4.1 `export_jobs`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | BIGSERIAL | 主键 |
| `export_id` | VARCHAR(32) | 对外 ID，`exp_` 前缀，唯一 |
| `user_id` | BIGINT | 发起人；下载与审计依据 |
| `source_type` | VARCHAR(16) | `answer` / `report`（11.12 仅 `answer`） |
| `source_id` | VARCHAR(32) | 答案 ID（`answer_id`） |
| `format` | VARCHAR(8) | `png` / `pdf` / `xlsx` / `csv` / `json` |
| `status` | VARCHAR(16) | `queued` / `running` / `ready` / `failed` / `expired` |
| `title` | VARCHAR(120) | 解析后的标题 |
| `view_spec` | JSON | 版式参数（纸张、方向、是否含引用、水印文案、最大行数） |
| `answer_blocks` | JSON | Envelope 快照：`blocks`、`citations`、`meta` 子集 |
| `component_versions` | JSON | `[{key, version}]`，来自快照 |
| `registry_version` | VARCHAR(16) | 组件注册表版本 |
| `data_version` | VARCHAR(32) | 数据版本/导入批次 |
| `data_hash` | VARCHAR(80) | 数据规范化哈希，`sha256:` 前缀 |
| `renderer_version` | VARCHAR(16) | 渲染模板/渲染器版本 |
| `file_path` | VARCHAR(255) | 相对存储根路径；不对外暴露 |
| `file_size` | BIGINT | 字节 |
| `sha256` | VARCHAR(80) | 产物哈希，用于去重与校验 |
| `error_code` | VARCHAR(32) | 失败码 |
| `error_message` | TEXT | 可读原因（不含堆栈） |
| `created_at` | TIMESTAMPTZ | 创建时间 |
| `started_at` | TIMESTAMPTZ | 开始渲染 |
| `finished_at` | TIMESTAMPTZ | 完成/失败 |
| `expires_at` | TIMESTAMPTZ | 默认创建后 7 天 |
| `download_count` | INT | 下载次数 |

索引：`(user_id, created_at)`、`(status, created_at)`、`(expires_at)`、`(source_type, source_id)`。

### 4.2 `view_spec` 与 `answer_blocks` 的职责

- `view_spec`：只放版式，不放数据。字段：`orientation`（portrait/landscape）、`include_citations`（bool）、`watermark`（bool）、`watermark_text`（服务端拼接）、`max_rows`（≤100）、`theme`（`gov-baseline`）。
- `answer_blocks`：不可变快照，含 `answer_id`、`answer_markdown`、`blocks`、`citations`、`meta.generated_at`、`meta.data_version`、`meta.data_hash`、`meta.registry_version`。
- 渲染只读快照；**不得**读 `chat_messages` 的当前值或重新调用 AI。

### 4.3 数据哈希与复现

```text
data_hash = "sha256:" + sha256(canonical_json({
  "data_version": "<dv>",
  "rows": [
    {"indicator_code": "...", "region_code": "...", "period": "...", "value": 123.4}
  ]
}))
```

规则：

1. `rows` 按 `(indicator_code, region_code, period)` 升序；`value` 为 null 时保留 null。
2. 数值按指标精度归一化后再哈希（避免浮点尾差）。
3. 哈希在答案生成时计算并写入 `meta.data_hash`；导出时校验快照哈希格式与覆盖范围，不回查数据。
4. 复现条件：同一 `answer_blocks` + 同一 `view_spec` + 同一 `renderer_version` + 同一 `format` → 产物字节一致（字体与渲染器版本固定）。
5. 若渲染器升级导致版式变化，旧产物不重渲染；新任务记录新的 `renderer_version`。

## 5. API

### 5.1 创建导出

`POST /api/v1/exports`

```json
{
  "source_type": "answer",
  "source_id": "ans_20261110_0001",
  "format": "pdf",
  "title": "2025 年镇街常住人口排名",
  "options": {
    "orientation": "portrait",
    "include_citations": true,
    "watermark": true,
    "max_rows": 100
  }
}
```

响应 `202 Accepted`：

```json
{
  "data": {
    "export_id": "exp_20261110_0001",
    "status": "queued",
    "format": "pdf",
    "created_at": "2026-11-10T10:05:00+08:00",
    "expires_at": "2026-11-17T10:05:00+08:00"
  },
  "meta": {"request_id": "req_20261110_0002"}
}
```

校验顺序：登录 → 角色/permission → `source_id` 可见性 → `format` 必填与枚举 → 快照存在与完整 → 格式适用性 → 体积预估 → 入队。任一步失败不创建任务。

### 5.2 查询状态

`GET /api/v1/exports/{export_id}`

```json
{
  "data": {
    "export_id": "exp_20261110_0001",
    "status": "ready",
    "progress": 100,
    "format": "pdf",
    "file_size": 184320,
    "sha256": "sha256:1111111111111111111111111111111111111111111111111111111111111111",
    "download_url": "/api/v1/exports/exp_20261110_0001/download?token=<signed>",
    "expires_at": "2026-11-17T10:05:00+08:00",
    "error": null
  },
  "meta": {"request_id": "req_20261110_0003"}
}
```

`status` 取值：`queued`（排队）、`running`（渲染中，`progress` 0–99）、`ready`（可下载）、`failed`（`error` 有值）、`expired`（文件已清理）。

### 5.3 下载

`GET /api/v1/exports/{export_id}/download`

- 校验登录态、`user_id` 与签名 token；302 跳转到短时签名地址或直接流式返回。
- 签名 token：绑定 `export_id + user_id`，TTL 10 分钟；不可转让、不可公开分享。
- `Content-Disposition`：`attachment; filename*=UTF-8''<encoded>`，文件名含标题与时间。
- 文件过期：410 `EXPORT_EXPIRED`；无权限：403 `EXPORT_FORBIDDEN`；不存在：404 `EXPORT_NOT_FOUND`。
- 不提供静态目录直链；Nginx 不暴露 `data/exports/`。

### 5.4 权限

| 角色 | 导出自己的答案 | 导出他人的答案 | 说明 |
|---|---|---|---|
| 游客 | 否 | 否 | 403 `EXPORT_FORBIDDEN`；即使答案本身可读 |
| 申请者（待批准） | 否 | 否 | 403；提示"待管理员批准" |
| 查看者 | 是 | 否 | 仅本人会话内答案 |
| 编辑者 | 是 | 否 | 与查看者相同导出范围 |
| 管理员 | 是 | 是 | 需写审计 |
| 审批者 | 是 | 是 | 需写审计 |

补充规则：

1. 权限以服务端为准；客户端隐藏按钮不是安全措施。
2. "已批准"= 用户 `status=active` 且角色属于上表允许项。
3. 权限位：`export.self`、`export.any`；角色到权限位的映射由服务端配置，不写死在客户端。
4. 05 §9 已登记六类身份（游客/申请者/查看者/编辑者/管理员/审批者）；本表按 05 §9 与 [23](23-auth-and-application-spec.md) 执行，权限位为 `export.self`、`export.any`。

### 5.5 错误码

| code | HTTP | 说明 |
|---|---|---|
| `EXPORT_FORMAT_REQUIRED` | 422 | 未提供格式（不设默认） |
| `EXPORT_FORMAT_UNSUPPORTED` | 422 | 该格式不适用于当前答案（如 CSV 多表） |
| `EXPORT_FORBIDDEN` | 403 | 游客/申请者/越权/答案不在可见范围 |
| `EXPORT_SOURCE_NOT_FOUND` | 404 | `answer_id` 不存在或已删除 |
| `EXPORT_NOT_FOUND` | 404 | 导出任务不存在或不属于当前用户 |
| `EXPORT_EXPIRED` | 410 | 产物已过期清理 |
| `EXPORT_TOO_LARGE` | 413 | 快照/产物超过体积上限 |
| `EXPORT_SNAPSHOT_INVALID` | 422 | 快照缺字段、哈希格式错误、组件版本非法 |
| `EXPORT_FAILED` | 500 | 渲染失败（如 Chromium 不可用） |
| `RATE_LIMITED` | 429 | 单用户并发/频率超限 |

## 6. 渲染

### 6.1 处理管线

```text
queued
  → 加载 export_job 快照
  → 校验快照（字段/哈希格式/组件版本/格式适用性）
  → 构建渲染模型（标题、块、引用、页脚、水印）
  → 选择渲染器（png/pdf: Chromium；xlsx: openpyxl；csv: csv）
  → 渲染到临时文件
  → 计算 sha256、文件大小
  → 移动到存储路径，status=ready
  → 失败：status=failed + error_code，临时文件清理
```

### 6.2 PNG / PDF

- 使用服务端无头 Chromium（Playwright）渲染**服务端模板**，模板只接受渲染模型；不加载业务前端、不执行用户脚本。
- Chromium 启动参数：禁用外部网络请求、禁用插件、禁用 GPU；页面内所有资源（字体、Logo）为本地文件。
- 截图：`deviceScaleFactor=2`，宽度 750px 逻辑宽度（与小程序视觉一致），高度按内容自适应，超长图限制 8000px。
- PDF：A4，纵向，边距 12mm，页脚含页码、导出编号、生成时间；内容超 2 页时截断表格行并标注"余下数据见 XLSX"。
- Pillow 作为降级：Chromium 不可用时，PNG 用 Pillow 绘制简化汇报卡（标题 + 指标 + 来源 + 水印）；PDF 无降级，返回 `EXPORT_FAILED` 并提示稍后重试。
- 水印：对角重复文字（显示名 + `yyyy-MM-dd HH:mm` + "内部资料"），透明度 0.08–0.12，不遮挡数值。

### 6.3 XLSX

- `openpyxl`，三个工作表：
  - `答案摘要`：标题、问题摘要、生成时间、数据时效、数据版本、导出人、导出编号、格式说明。
  - `数据`：按块展开为表；列头含指标名与单位；数值写为数字类型（不是字符串）；`null` 留空；不写 0。
  - `引用`：指标、区域、期、来源、`data_as_of`、`citation_id`。
- 不写公式、不写宏、不做透视表；冻结首行；列宽按内容估算并设上限 40 字符。
- 字体名用"等线"（常见 Office 客户端可显示）；不嵌入字体；中文长度按字符计。
- 超过 100 行：截断并在摘要页标注；超过体积上限：`EXPORT_TOO_LARGE`。

### 6.4 CSV

- Python 标准库 `csv.writer`，`utf-8-sig` 编码（兼容 Excel 中文）。
- 只输出一张表：表头一行 + 数据行；单元格内的逗号、引号、换行按 RFC 4180 转义。
- `null` 输出空字符串，不以 0 代替；数值不带千分位。
- 文件名：`<标题>_<期>_<导出编号>.csv`；标题非法字符替换为下划线。
- 无表格或有多张表：`EXPORT_FORMAT_UNSUPPORTED`，提示改用 XLSX/PDF。

### 6.5 中文字体

- 必须随部署打包 `Noto Sans CJK SC`（OFL）或 `Source Han Sans SC`，放 `deploy/fonts/`；不得依赖宿主机字体。
- 模板通过 `@font-face` 使用本地字体；PDF 嵌入子集。
- 必测字形：滘、窖、磐、霖、埔、锡、揭、粤、肇、榕（覆盖揭东地名用字）。
- 字体缺失时启动自检失败（`/ready` 返回失败），不允许静默回退到无中文字体。

### 6.6 存储与清理

| 项 | 11.12 方案 | 后续 |
|---|---|---|
| 存储 | 本地 `services/api/data/exports/{yyyy}/{mm}/` | 对象存储（S3 兼容/政务云） |
| 路径 | DB 存相对路径；不暴露绝对路径 | 同 |
| 权限 | 目录与文件 0600；仅 API 进程可读 | 私有桶 + 签名 URL |
| 保留 | 7 天（`expires_at`） | 可配置 7–30 天 |
| 清理 | 每小时扫描过期任务；启动时补扫；删除文件 + `status=expired` | 生命周期规则 |
| 审计保留 | 180 天（不含文件） | 按合规要求 |

### 6.7 资源与并发

| 项 | 值 | 说明 |
|---|---:|---|
| 渲染并发 | 2 | 单进程；后台任务用 DB 队列 |
| 单任务超时 | 60 s | 超时 `EXPORT_FAILED`（`timeout`） |
| Chromium 内存上限 | 512 MB | 复用单个 browser，按任务新建 context |
| PNG 上限 | 3 MB / 8000 px 高 | 超出改 PDF |
| PDF 上限 | 10 MB / 2 页 | 超出截断并提示 |
| XLSX/CSV 上限 | 10 MB / 5 MB | 超出 `EXPORT_TOO_LARGE` |
| 排队上限 | 每用户 3 个未完成任务 | 超出 429 |
| 频率 | 每用户 10 次/小时 | 超出 429 |

## 7. 界面

### 7.1 格式选择

1. 四张格式卡：PNG、PDF、XLSX、CSV；初始**无选中**。
2. 卡片显示用途与限制（如"CSV 仅单表""PDF 适合打印"）。
3. 未选择时"导出"按钮禁用；选择后才可提交。
4. 不提供"默认格式""始终使用此格式"设置；每次导出都重新选择。
5. 不适用格式置灰并给原因；不自动切换、不静默降级。

### 7.2 状态与进度

| 状态 | 界面 | 操作 |
|---|---|---|
| idle | 格式卡 | 选择 |
| submitting | 按钮 loading | 不可重复提交 |
| queued | "排队中，前面 N 个" | 可取消（P1） |
| running | 进度条（0–99） | 可离开页面，稍后回看 |
| ready | 文件大小 + 下载/分享 | 下载、分享、重新导出 |
| failed | 错误码对应的可读文案 + 重试 | 重试（新任务） |
| expired | "文件已过期，请重新导出" | 重新导出 |

进度为估算值：入队 10%、构建模型 30%、渲染 80%、写盘 100%。不使用定时轮询以外的"假动画"；轮询间隔 1 s，最多 60 次。

### 7.3 下载与分享

- 小程序：PNG 用 `wx.saveImageToPhotosAlbum`（先处理授权拒绝）；PDF/XLSX 用 `wx.downloadFile` + `wx.openDocument`；CSV 不能保证预览，提供"复制下载链接"，由浏览器打开（需真机验证）。
- 分享：`wx.shareAppMessage` 携带 `export_id`；接收方打开时重新校验权限，无权限跳 MP08。
- 后台：直接下载；提供"复制链接"（10 分钟有效，绑定当前用户）。
- 下载失败：区分网络错误、链接过期（提示重新导出）、权限变化（提示无权限）。

### 7.4 移动端限制

- 小程序包体与内存有限：不在端上合成 PDF/XLSX，全部服务端生成。
- 弱网：下载支持断点重试（P1）；11.12 至少显示"重新下载"。
- 文件名在微信内可能被截断；下载页同时显示标题与格式。

### 7.5 无障碍与文案

- 格式卡有文字说明，不只靠图标。
- 进度与结果通过文字播报（`aria-live` 等价能力在 MP 用 toast）。
- 错误文案不出现堆栈、路径、内部主机名。

## 8. 安全与审计

| 项 | 要求 |
|---|---|
| 权限 | 服务端逐次校验；游客、申请者、越权答案一律 403；客户端隐藏按钮不作为依据 |
| 链接 | 下载 token 短时（10 分钟）、绑定用户与导出 ID；不可公开转发 |
| 水印 | 显示名 + 时间 + "内部资料"；不可关闭（管理员也一样） |
| PII | 不导出 openid、手机号、密码、token；水印只用显示名 |
| 快照 | 只读；导出不复查数据库；哈希校验覆盖范围 |
| 文件 | 0600、非静态目录、路径不进日志 |
| 审计 | 记录 `export.requested`、`queued`、`ready`、`failed`、`downloaded`、`expired`、`denied`；字段含 user、export_id、format、source_id、ip、ua、结果 |
| 保留 | 文件 7 天；审计 180 天；答案快照随会话删除策略处理 |
| 限流 | 每用户 3 并发、10 次/小时；异常用户临时封禁（P1） |
| 日志 | 不记录密钥、token、完整下载 URL；错误只记录 code 与简短原因 |

拒绝场景必须写审计：游客尝试、申请者尝试、越权访问他人答案、签名 token 失效重试。

## 9. 验收与测试矩阵

### 9.1 格式

| 用例 | 输入 | 期望 |
|---|---|---|
| PNG 生成 | 含排名块 + 来源块的答案 | 200/202 → ready；PNG 签名正确；含标题、数值、来源、水印；中文无方框 |
| PDF 生成 | 同上 | PDF 可打开；页脚含导出编号与页码；文本可检索到标题与"内部资料" |
| XLSX 生成 | 含指标 + 表格 + 引用 | 3 个工作表；数值为数字类型；`null` 为空；无公式 |
| CSV 生成 | 仅一张表 | UTF-8 BOM；表头 + 行；无 0 替代空值 |
| 多表 CSV | 两张表 | 422 `EXPORT_FORMAT_UNSUPPORTED`；提示 XLSX |
| 纯文本答案 CSV | 无表格 | 422；提示 PDF/XLSX |
| JSON（可选） | 任意答案 | 快照完整、可反序列化；含 `data_hash` |

### 9.2 权限

| 用例 | 期望 |
|---|---|
| 游客导出 | 403 `EXPORT_FORBIDDEN`；按钮不可见且接口拒绝 |
| 申请者（待批准）导出 | 403；提示待批准 |
| 查看者导出自己的答案 | 202 → ready |
| 查看者导出他人答案 | 403 或 404（不泄露存在性） |
| 管理员导出他人答案 | 202 → ready；写审计 |
| 过期 token 下载 | 403/410；不返回文件 |
| 无 token 直接访问存储路径 | 404（目录不可访问） |

### 9.3 契约与一致性

| 用例 | 期望 |
|---|---|
| 缺少 `format` | 422 `EXPORT_FORMAT_REQUIRED`；不创建任务 |
| 非法 `format` | 422 |
| 导出后修改底层数据 | 再次导出同一答案仍与首次内容一致（快照） |
| 同一快照导出两次 | `sha256` 一致（同渲染器版本） |
| 快照缺 `blocks` | 422 `EXPORT_SNAPSHOT_INVALID` |
| 组件被禁用 | 历史导出仍可下载；新导出走 fallback 并在内容中标注 |
| 文件过期 | 410 `EXPORT_EXPIRED`；重新导出成功 |
| 并发 3 个任务 | 按队列执行，不超时、不串文件 |
| 超大答案 | 413 或截断并提示；不生成损坏文件 |
| 无数据答案 | 正常导出 `notice`，不补 0、不编造 |
| 字体缺失 | 启动自检失败；不产出方框字 |

### 9.4 验证方式

- 后端单测：权限矩阵、格式校验、快照哈希、文件名清洗。
- 集成测试：`POST /exports` → 轮询 → 下载，校验签名与 MIME。
- 手动路径：小程序真机导出 PNG/PDF；后台导出 XLSX/CSV 并用 Office/Excel 打开。
- 视觉抽检：PDF/PNG 的中文字形、水印透明度、数值对齐。
- 审计核对：每个用例都能在 `audit_logs` 找到对应事件。

## 10. 开放问题

1. 游客是否允许"查看但不导出"的答案分享链接？当前结论是不允许导出，分享后接收方仍按权限校验。
2. 六角色（游客/申请者/查看者/编辑者/管理员/审批者）已在 05 §9 登记；本文只定义权限位，角色存储是否将审批者作为独立角色或 admin 权限位由实现批次决定。
3. `renderer_version` 是否与组件注册表版本合并？当前分开，便于独立升级版式。
4. CSV 是否需要附带 sidecar JSON 元数据？当前不提供，元数据放表头与文件名。
5. 对象存储/政务云的文件加密与生命周期规则待部署方案（ADR-004）确定后再补。
6. 小程序端 CSV 预览能力需真机验证；若不支持，是否直接隐藏 CSV 入口，需与产品确认。
