# apps/admin · Web 管理后台

> 状态：B05/C02 Demo v0 可视化后台已可运行（登录、总览、数据列表、导入、申请审批、用户、审计；问答记录/组件库/设置标注未实现）。

## 职责

- 数据管理员登录、总览、数据值列表与详情、指标元数据查看。
- Excel 导入、导入记录、错误明细。
- 账号申请审批、用户角色与状态维护、审计日志查看。
- 11.12 只做 Web 可视化基线，视觉不锁定品牌；不做小程序/后端/部署代码。

## 技术栈

Vue 3 + Vite + TypeScript + Element Plus + Pinia + Vue Router + ECharts + axios。

## 运行

前提：Node.js 22+、pnpm 11+。仓库根是 pnpm workspace，`apps/admin` 是其中一个包。

```bash
cd <repo-root>
pnpm install
pnpm --filter @ijd/admin dev
```

开发地址：`http://127.0.0.1:5173`。后端默认 `http://127.0.0.1:8000`。

构建与本地预览：

```bash
pnpm --filter @ijd/admin build
pnpm --filter @ijd/admin preview
```

- `pnpm build` 依次执行 `vue-tsc`（应用与 `vite.config.ts` 类型检查）与 `vite build`。
- `pnpm typecheck` 只跑应用类型检查。
- 产物输出到 `apps/admin/dist/`，已由根目录 `.gitignore` 忽略。

## 环境变量

复制 `.env.example` 为本机 `.env`（已被 gitignore），只填写非敏感配置：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `VITE_API_BASE_URL` | `http://127.0.0.1:8000/api/v1` | 已包含 `/api/v1` 前缀；末尾斜杠会被去除 |

两种联调方式：

1. 绝对地址（默认）：后端需在 `services/api/.env` 的 `CORS_ORIGINS` 中允许 `http://127.0.0.1:5173`。
2. 相对地址：设置 `VITE_API_BASE_URL=/api/v1`，走 `vite.config.ts` 的 `/api` 开发代理，无需改后端 CORS。

部署到 Nginx 同源时，构建前设置 `VITE_API_BASE_URL=/api/v1`，由 Nginx 把 `/api/` 反代到后端。

仓库不提交 `.env`、令牌或任何密钥；前端只保存登录令牌与用户摘要，不保存 API Key。

## 目录

```text
src/
├── api/            # axios 客户端、信封/错误解析、端点与类型
├── components/     # 页面头、区块卡、指标卡、状态标签、图表、占位页
├── composables/    # useRequest（加载/错误/防过期响应）
├── layouts/        # AdminLayout：左侧导航 + 顶栏
├── router/         # 路由与角色守卫
├── stores/         # Pinia auth store
├── styles/         # 设计令牌、Element Plus 变量桥接、基础样式
├── utils/          # 数值/时间格式化、角色与状态文案、脱敏
└── views/          # 页面
```

## 页面与路由

| 路由 | 页面 | 角色 | 接口 |
|---|---|---|---|
| `/login` | 登录 | 公开 | `POST /auth/login` |
| `/overview` | 总览 | 已登录 | `GET /dashboard/overview`、`GET /admin/imports`、`GET /admin/applications?status=pending` |
| `/data` | 数据列表 | viewer/editor/admin/approver | `GET /data-values`、`GET /regions`、`GET /indicators`、`GET /indicators/{id}` |
| `/import` | 数据导入 | editor/admin | `POST /admin/imports`、`GET /admin/imports`、`GET /admin/imports/{id}`、`GET /admin/imports/{id}/errors` |
| `/applications` | 申请审批（批准后一次性展示初始密码） | admin/approver | `GET /admin/applications`、`POST /admin/applications/{id}/approve`、`POST /admin/applications/{id}/reject` |
| `/users` | 用户管理 | admin | `GET /admin/users`、`PATCH /admin/users/{id}` |
| `/audit` | 审计日志 | admin | `GET /admin/audit-logs` |
| `/ai-logs`、`/components`、`/settings` | 占位页 | 已登录 | 不请求接口，明确标注“B05 未实现” |
| `/403`、`/404` | 无权限、页面不存在 | — | 不请求接口 |

路由守卫：无令牌跳 `/login?redirect=...`；令牌失效（401）清除会话并回登录页；角色不足跳 `/403`。菜单按角色裁剪，但权限判定以服务端为准。

## 后端依赖状态

- 已实现：B04 区域/指标/数据值/排名/对比/总览；B05 `/auth/*`、`/admin/*`、Excel 导入；B08 AI/导出（后台不直接调用 AI/导出）。
- 接口失败时页面显示 401/403/404 的可读提示与重试入口，不展示假数据。
- 错误响应按 `{error:{code,message,details}, request_id}` 解析，界面展示中文提示并附带 `request_id`。

## 设计约定

- 中性政务基线：白/浅灰底、深色文字、单一克制蓝色；无渐变装饰、无插画、无花哨动效。
- 令牌集中在 `src/styles/tokens.css`，Element Plus 通过 `src/styles/element.css` 读取同一套变量。
- 数值只按指标精度格式化，空值显示“暂无数据/不适用”，不补 0；不同单位的指标不使用同一线性刻度强行对比。
- 全局标注“演示环境 Demo v0”与“演示数据”。

## 边界

- 只放后台代码；不放小程序/后端/部署脚本。
- 接口以 `docs/agent/05-architecture.md`、`docs/agent/23-auth-and-application-spec.md` 与 OpenAPI 为准。
- 不直连 LLM；不在前端保存密钥。
- 不使用 Element Plus 与 ECharts 之外的 UI 框架。

## 已知限制

- Element Plus 采用完整引入，主包约 1.1 MB（gzip 约 380 KB）；按需引入列为后续优化项。
- 审计页保留时间范围控件，但 Demo v0 的 `GET /admin/audit-logs` 未提供 `date_from`/`date_to` 参数，选中范围时页面会明示“未按时间裁剪”；接口补齐后无需改前端。
- 审计列表不含操作者姓名，前端在缺少 `user_display_name` 时显示“用户 #ID”。
- 申请列表接口不返回申请说明与关联用户 ID，因此“不能审批本人申请”以服务端 `CANNOT_APPROVE_SELF` 为准。
- 首次登录强制改密、导出任务、指标目录/数据质量页属于 P1，本次未实现。
- 未做端到端自动化测试；`e2e/` 与 `tests/` 仍为占位目录。

## 下一步

1. 联调登录、审批与用户维护的真实链路（B05 已就绪）。
2. 按需引入 Element Plus 与图表按路由拆分，压缩首屏体积。
3. 补 `e2e/` 主路径用例（登录、审批、导入错误报告）。
4. 补 `/admin/data-values` 写接口后的数据编辑抽屉。
