# contracts · OpenAPI 契约

> 状态：已生成 B04 只读查询端点；认证/申请、AI、管理端端点待补。

## 职责

- `openapi.json`：后端导出的唯一 API 契约。
- `examples/`：请求/响应示例（脱敏/演示数据）。
- 前端类型生成源；后端接口验收依据。

## 规则

- API 改动先改 `docs/agent/05-architecture.md`，再改代码，再导出 OpenAPI。
- `openapi.json` 提交仓库；CI 可检查是否过期。
- 示例不放真实敏感数据/密钥。
- 不手写 SDK；前端用生成的类型 + 轻量 client。

## 命令（B-002 后）

```bash
# 后端运行后导出（FastAPI 默认路径）
curl http://localhost:8000/openapi.json -o contracts/openapi.json
```

或从 `services/api` 直接生成：

```bash
python -c "import json; from app.main import app; open('../../contracts/openapi.json','w',encoding='utf-8').write(json.dumps(app.openapi(), ensure_ascii=False, indent=2) + '\n')"
```
