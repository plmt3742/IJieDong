# services/api · FastAPI 后端

> 状态：占位（B-002 创建可运行脚手架）。

## 职责

- 认证/RBAC、区域/指标/数据值 API。
- Excel 导入、校验、错误报告。
- AI Agent（工具调用 + ChartSpec + 引用）。
- 审计、日志、健康检查。
- OpenAPI 导出。

## 计划技术栈

Python 3.13 + FastAPI + Pydantic v2 + SQLAlchemy 2.0 + Alembic + PostgreSQL。

## 目录（计划）

```text
app/
├── main.py
├── core/          # config/logging/errors/security/request_id
├── db/            # engine/session/base
├── models/
├── schemas/
├── api/v1/        # auth/regions/indicators/data/ai/admin/health
├── services/      # data/import/auth/audit
├── ai/            # client/tools/agent/prompts/chart/validator
└── utils/
alembic/
tests/
scripts/
```

## 命令（B-002 后）

```bash
uv sync
uv run uvicorn app.main:app --reload
uv run ruff check .
uv run pytest
```

## 边界

- 不放前端代码；不把真实数据/密钥提交。
- LLM 只调用白名单工具；不生成 SQL/JS。
- API/数据模型以 `docs/agent/05-architecture.md` 为准。
- 迁移必须可升级/回滚。

## 下一步（B-002）

1. 脚手架 + `/health` + 配置/日志/CORS。
2. PostgreSQL 连接 + Alembic。
3. OpenAPI 导出。
4. 测试/lint/CI。
