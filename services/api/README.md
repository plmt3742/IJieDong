# services/api · FastAPI 后端

> 状态：B00 + B01 + B02 + B04 + B05 + B08 可运行 Demo v0 API（B-002）。服务可启动、可测试；12 张表、迁移 0001/0002/0003、合成种子、区域/指标/数据/排名/对比/总览、认证/申请/审批/导入、AI 问答与四格式导出已完成；119 tests；OpenAPI 35 paths。

## 职责

- 认证/RBAC、区域/指标/数据值 API。
- Excel 导入、校验、错误报告。
- AI Agent（工具调用 + ChartSpec + 引用）。
- 审计、日志、健康检查。
- OpenAPI 导出。

## 当前能力（B00）

- `app.main:create_app()` 应用工厂，标题 `i揭东 API`，版本 `0.1.0`。
- 基于 `pydantic-settings` 的环境配置，读取 `.env`，不提交真实密钥。
- SQLAlchemy 2.0 async engine / `async_sessionmaker` / `get_db` 依赖；SQLite 目录自动创建。
- 请求 ID 中间件：接受 `X-Request-ID`，缺失时生成 UUID4，并写入响应头与日志。
- 统一错误响应：`{"error": {"code", "message", "details"}, "request_id"}`；500 不返回堆栈。
- 健康检查：`GET /health`（不查库）、`GET /ready`（`SELECT 1`，失败返回 503 `NOT_READY`）。
- 同时挂载根路径与 `/api/v1` 版本路径。

## 当前能力（B01）

- 12 张 Demo v0 表：`regions`、`region_aliases`、`indicators`、`data_sources`、`users`、`import_jobs`、`data_values`、`user_applications`、`chat_sessions`、`chat_messages`、`export_jobs`、`audit_logs`。
- `data_values` 为受控观测表（契约名 `observations`），含 `quality_status`、`dimension_hash`、`version`。
- Alembic 初始迁移 `0001`：`alembic upgrade head` / `alembic downgrade base` 均通过；`alembic check` 无差异。
- 模型测试覆盖表注册、SQLite 友好主键、唯一约束、索引、角色检查与 mapper 配置。

## 当前能力（B02）

- 确定性合成种子：227 区域、15 指标、1608 个适用数据值、454 个文本值、42 个缺失值。
- 覆盖区/13 行政镇街/2 开发区/211 村居；GDP 仅 3 行，行政村数量 14 行，耕地/林地各 225 行。
- `玉窖镇 -> 玉滘镇` 别名；`演示数据（合成）` 数据源与 `seed_demo.py` 导入批次。
- 种子幂等；`--check` 只打印计数，不写库。

## 当前能力（B04）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/regions` | 区域分页筛选（层级/父级/名称/启用） |
| GET | `/api/v1/regions/tree` | 区域树（root_code/depth） |
| GET | `/api/v1/regions/{id}` | 区域详情 + 父级 |
| GET | `/api/v1/regions/{id}/profile` | 文本简介/特色 + 适用指标 + 数据时效 |
| GET | `/api/v1/indicators` | 15 个指标元数据 |
| GET | `/api/v1/indicators/{id}` | 指标详情 |
| GET | `/api/v1/data-values` | 数据值分页查询 |
| GET | `/api/v1/data-values/rank` | 排名（排除空值/缺失；可选开发区） |
| GET | `/api/v1/data-values/compare` | 2–20 区域对比 + 差异 |
| GET | `/api/v1/dashboard/overview` | 区级核心指标 + 镇街数 + 数据时效 |

`contracts/openapi.json` 已由 FastAPI 生成，包含 35 个路径；认证/申请/审批/用户/审计/导入、AI、导出端点已补齐。

## 当前能力（B05）

- JWT 登录/me/改密/退出；小程序申请/状态；管理员申请列表/批准/驳回；用户列表/更新；审计列表。
- Excel 导入：上传/批次/错误报告；atomic/partial；空值为 missing，不写 0。
- Web 后台：登录/总览/数据/导入/申请/用户/审计；`apps/admin`。

## 当前能力（B08）

- `POST /api/v1/ai/chat`：确定性规则 Agent（无 Key）+ OpenAI 兼容 LLM 通道（有 Key）；AnswerBlocks/引用/无数据拒答/会话落库。
- 10 个只读工具；五层校验；限流 10/min/用户、5/day/游客 IP。
- PNG/PDF/XLSX/CSV 导出；`export_jobs` 快照、下载端点、7 天过期字段。

## 技术栈

Python 3.13 + FastAPI + Pydantic v2 + SQLAlchemy 2.0（async）+ SQLite（11.12 演示）。

- 演示环境：SQLite 文件 `./data/app.db`，已加入 `.gitignore`。
- 生产目标：PostgreSQL 16；切换只改 `DATABASE_URL`。
- Alembic 迁移与领域模型属于 B01，已完成；种子数据属于 B02。

## 目录

```text
app/
├── main.py              # create_app 工厂、CORS、路由挂载
├── core/                # config/logging/errors/request_id
├── db/                  # base/session
├── api/v1/              # router、health
├── models/              # 预留（B01）
├── schemas/             # 预留
├── services/            # 预留
├── ai/                  # 预留
└── utils/               # 预留
tests/
├── conftest.py
└── unit/
```

## 运行

```bash
cd services/api
python -m pip install -r requirements.txt
python -m alembic -c alembic.ini upgrade head
python scripts/seed_demo.py
python scripts/create_admin.py --username admin
python -m uvicorn app.main:app --reload
```

默认地址：`http://127.0.0.1:8000`。

数据库迁移：`python -m alembic -c alembic.ini upgrade head`；回滚：`python -m alembic -c alembic.ini downgrade base`。

种子检查：`python scripts/seed_demo.py --check`；重新播种：`python scripts/seed_demo.py`（幂等）。

| 路径 | 用途 |
|---|---|
| `GET /health` | 存活检查，不查库 |
| `GET /ready` | 就绪检查，执行 `SELECT 1` |
| `GET /api/v1/health` | 版本化存活检查 |
| `GET /docs` | FastAPI 自动文档 |

首次启动或访问 `/ready` 时会创建 `data/app.db`，属预期行为。

## 测试

```bash
cd services/api
python -m compileall app tests
python -m pytest -q
```

测试使用临时 SQLite 文件，不写入仓库内 `data/app.db`。

## 配置

复制模板并填写本地值：

```bash
copy .env.example .env
```

- `APP_ENV`：默认 `development`。
- `DATABASE_URL`：默认 `sqlite+aiosqlite:///./data/app.db`。
- `CORS_ORIGINS`：逗号分隔；为空时不启用跨域。
- `LOG_LEVEL`：默认 `INFO`。
- `REQUEST_ID_HEADER`：默认 `X-Request-ID`。
- `LLM_PROVIDER` / `LLM_BASE_URL` / `LLM_MODEL` / `LLM_API_KEY`：可选，当前留空。

`.env` 与任何真实密钥不得提交；仓库只保留 `.env.example`。

## 代码质量

`pyproject.toml` 已配置 pytest（`testpaths=tests`、`pythonpath=["."]`）与 ruff（`line-length=100`、`target-version=py313`）。

当前环境未安装 ruff；如需执行，先安装开发依赖：

```bash
python -m pip install -e ".[dev]"
python -m ruff check .
```

## 边界

- 不放前端代码；不把真实数据/密钥提交。
- LLM 只调用白名单工具；不生成 SQL/JS。
- API/数据模型以 `docs/agent/05-architecture.md` 与 `docs/agent/21-technical-architecture-v2.md` 为准。
- 迁移必须可升级/回滚。
- 本批次已包含领域模型、Alembic、种子数据与业务端点；B05/B08 已追加认证/管理/导入/AI/导出。

## 下一步

1. 真实 LLM Key 联调 + 50 题评测；回答缓存。
2. `/admin/data-values` 写接口、审计日期筛选。
3. AppID/域名/服务器到位后部署小服务器 + 小程序真机。
4. Step 6 文档收口与主路径联调。
