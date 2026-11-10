# contracts · OpenAPI 契约

> 状态：已生成 B04 查询 + B05 认证/申请/审批/导入 + B08 AI/导出，共 35 paths；OpenAPI 3.1.0。

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
cd services/api
python scripts/export_openapi.py
```
