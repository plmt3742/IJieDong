# apps/admin · Web 管理后台

> 状态：占位（B-002 创建可运行脚手架）。

## 职责

- 数据管理员登录、数据值列表/筛选/编辑。
- Excel 导入、导入记录、错误报告。
- 审计日志、用户/权限（P1）。
- 图表预览、数据覆盖率（P1）。

## 计划技术栈

Vue 3 + Vite + TypeScript + Element Plus + ECharts + Pinia + Vue Router。

## 目录（计划）

```text
src/
├── api/            # HTTP client、端点、类型
├── components/     # 通用组件
├── composables/    # useAuth/usePagination/useChart
├── layouts/        # AdminShell
├── router/
├── stores/
├── styles/
├── types/
├── utils/
└── views/          # 页面
```

## 边界

- 只放后台代码；不放小程序/后端/部署脚本。
- 接口以 `docs/agent/05-architecture.md` 与 OpenAPI 为准。
- 不直连 LLM；所有 AI 请求走后端。
- 不保存 API Key。

## 下一步（B-002）

1. Vite + Vue3 + TS 脚手架。
2. Element Plus、Router、Pinia、Axios。
3. ESLint/Prettier/typecheck。
4. 登录壳 + `/health` 联调。
