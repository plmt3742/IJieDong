# packages/contracts · 共享契约类型

> 状态：占位（B-002 创建）。

## 职责

- 从 `contracts/openapi.json` 生成 TypeScript 类型。
- 存放前端共享的 API 类型/常量（如错误码、枚举）。
- 不手写与 OpenAPI 重复的类型。

## 计划

```text
src/
├── generated/      # openapi-typescript 输出（生成物）
├── enums.ts        # 角色/状态/错误码常量
└── index.ts
```

## 命令（B-002 后）

```bash
pnpm --filter @ijiedong/contracts generate
```

## 边界

- 不放业务逻辑/页面/请求实现。
- 不修改生成物手写补丁；改 OpenAPI 后重新生成。
- 生成物提交仓库，保证前端可独立构建。
