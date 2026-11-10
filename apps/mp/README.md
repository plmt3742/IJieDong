# apps/mp · 原生微信小程序

> 状态：D01-D05 Demo v0 脚手架与页面已落地。TypeScript 编译、JSON 解析与结构校验通过；微信开发者工具与真机视觉验证未执行（当前环境无 DevTools）。

## 职责

- 首页总览、区域树/画像、指标详情。
- ChartSpec 图表渲染（Canvas 2D）。
- AI 问答、答案块、引用与追问。
- 账号申请/状态、管理员移动审批、导出。
- 游客、申请者、查看者、编辑者、管理员、审批者的前端可见性控制。

## 技术栈

- 原生微信小程序 + TypeScript + WXML + WXSS。
- 图表：自实现 Canvas 2D 渲染器，输入仅限 ChartSpec；未引入 echarts-for-weixin。
- 网络：`services/request.ts` 封装 `wx.request`，无第三方 HTTP 库。
- UI：原生组件与共享 WXSS 设计令牌；`tdesign-miniprogram` 已列入依赖但当前未导入，避免额外的 npm 构建步骤。

> 不做 H5；不使用 uni-app/Taro。

## 目录

```text
apps/mp/
├── project.config.json
├── project.private.config.json   # DevTools 生成，gitignore
├── package.json
├── tsconfig.json
├── .env.example
├── .gitignore
├── typings/
│   └── index.d.ts
└── miniprogram/
    ├── app.ts / app.json / app.wxss / sitemap.json
    ├── pages/
    │   ├── home/                  # MP01 首页
    │   ├── regions/               # MP02 区域导航
    │   ├── region-detail/         # MP03 区域画像
    │   ├── indicator-detail/      # MP04 指标详情
    │   ├── ai/                    # MP05 问答入口
    │   ├── chat/                  # MP06 答案会话
    │   ├── profile/               # MP08 我的/帮助
    │   ├── apply/                 # MP14 申请/状态
    │   ├── admin-approval/        # MP15 移动轻管理
    │   └── export/                # MP12 导出
    ├── components/
    │   ├── chart/                 # ChartSpec -> Canvas 2D / 表格降级
    │   ├── metric-card/           # 指标卡
    │   └── state-view/            # loading/empty/error/locked/no-permission
    ├── services/
    │   ├── config.ts              # 运行配置、API 路径、演示标记
    │   ├── request.ts             # wx.request Promise 封装、401、错误码
    │   └── api.ts                 # 区域/指标/数据/AI/认证/管理/导出
    ├── utils/
    │   ├── format.ts              # 数值、单位、日期、质量标签
    │   ├── storage.ts             # 本地存储命名空间
    │   ├── auth.ts                # 身份、令牌、游客 AI 配额
    │   └── application.ts         # 申请时间线与重提规则
    └── types/
        ├── api.ts
        ├── models.ts
        └── chart.ts
```

## 运行

1. 启动后端（`services/api`）：
   ```bash
   cd services/api
   python -m pip install -r requirements.txt
   python -m alembic -c alembic.ini upgrade head
   python scripts/seed_demo.py
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
   开发者工具模拟器用 `http://127.0.0.1:8000`；真机用本机局域网地址。
2. 安装小程序依赖并做类型检查：
   ```bash
   cd apps/mp
   npm install
   npm run typecheck
   ```
3. 用微信开发者工具打开 `apps/mp` 目录：
   - 当前 AppID 已写入 `project.config.json`；如更换主体或测试号，替换该文件的 `appid` 后重新导入。
   - 本地开发需在“详情 -> 本地设置”勾选“不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书”，否则本地 HTTP 请求会被拦截。
   - 项目使用 TypeScript 编译插件（`setting.useCompilerPlugins`）；修改 `.ts` 后由开发者工具编译，不产出 `dist/`。

### 本机服务器（局域网）

当前 Demo v0 以本机 Windows 工作站作为服务器：

- 后端监听 `0.0.0.0:8000`，Windows 防火墙对 `LocalSubnet` 放行 TCP 8000。
- 开发者工具模拟器使用 `127.0.0.1`；真机预览使用 `services/config.ts` 的 `LAN_BASE_URL`（当前 `http://10.62.172.85:8000/api/v1`）。
- 如果电脑局域网 IP 变化，修改 `LAN_BASE_URL` 后重新生成 Preview 二维码。
- 手机与电脑必须在同一局域网；公共网络/手机流量无法访问该地址。
4. 非 `develop` 环境没有默认 API 域名。首次打开后在开发者工具 Console 执行：
   ```js
   wx.setStorageSync('ijd:api_base_url', 'https://your-demo-host.example/api/v1')
   ```
   该值只保存在本机；`.env.example` 只作配置说明，微信运行时不会读取 `.env`。
5. 现有页面没有登录表单。联调已登录角色时，由后端认证流程或测试脚本写入：
   ```js
   wx.setStorageSync('ijd:token', '<test-jwt>')
   wx.setStorageSync('ijd:user', { id: 1, display_name: '测试用户', unit: '测试单位', role: 'admin', status: 'active' })
   ```
   不要提交真实令牌或账号。

## 配置

| 配置 | 位置 | 说明 |
|---|---|---|
| API Base | `services/config.ts` + `ijd:api_base_url` | `develop` 默认 `http://127.0.0.1:8000/api/v1`；其他环境必须显式配置 |
| 演示标记 | `DEMO_MODE` | 控制“演示数据”水印与来源文案 |
| 维护电话 | `MAINTAINER_PHONE` | 仓库内留空；部署前本地填写 |
| 游客 AI 配额 | `utils/auth.ts` | 5 次/设备/日，仅本地计数 |
| 导出水印 | `WATERMARK_TEXT` | `演示数据·内部资料` |

禁止把 AppSecret、JWT Secret、DeepSeek Key、数据库密码写入小程序代码或 `.env.example`。

## API 路径

| 能力 | 方法 | 路径 |
|---|---|---|
| 首页总览 | GET | `/dashboard/overview?period_year=2025` |
| 区域列表/树/详情/画像 | GET | `/regions`、`/regions/tree`、`/regions/{id}`、`/regions/{id}/profile` |
| 指标 | GET | `/indicators`、`/indicators/{id}` |
| 数据值/排名/对比 | GET | `/data-values`、`/data-values/rank`、`/data-values/compare` |
| AI 问答 | POST | `/ai/chat` |
| 当前用户 | GET | `/auth/me` |
| 申请/状态/退出 | POST/GET | `/auth/apply`、`/auth/application-status`、`/auth/logout` |
| 审批/用户/审计 | GET/POST/PATCH | `/admin/applications`、`/admin/applications/{id}/approve`、`/admin/applications/{id}/reject`、`/admin/users`、`/admin/users/{id}`、`/admin/audit-logs` |
| 导出 | POST/GET | `/exports`、`/exports/{id}`、`/exports/{id}/download` |

认证/AI/管理/导出端点已由 B05/B08 落地。前端保留未就绪降级：

- AI：请求失败时展示明确标注“演示回答”的结构示例，占位数字不作为统计结论。
- 管理：无权限或接口失败时展示“管理接口尚未就绪”的空状态。
- 导出：接口失败时提示“导出接口尚未就绪”，不生成空文件。
- 申请：接口不可用时保存本地演示记录，并明确标注“未提交服务器”。

## 身份与降级

| 身份 | 浏览数据 | AI | 导出 | 管理 |
|---|---|---|---|---|
| 游客 | 允许 | 每日 5 次 | 禁止 | 禁止 |
| 申请者 | 禁止，只显示状态 | 禁止 | 禁止 | 禁止 |
| viewer/editor | 允许 | 允许 | 允许 | 禁止 |
| admin/approver | 允许 | 允许 | 允许 | 允许（仅移动轻管理） |

- 401 或 `USER_DISABLED`：`request.ts` 清除本机令牌并通知页面回游客态。
- 申请者拦截在页面 `onLoad` 完成，不请求数据接口。
- 导出格式初始为未选择；未选择时“生成”按钮禁用，不设默认格式。

## ChartSpec

- 支持 `bar`、`hbar`、`line`、`pie`、`table`；最低保证 `bar` 与 `table`。
- `null` 表示无数据：柱状跳过该柱、折线断线、饼图过滤、表格显示“暂无数据”，不补 0。
- 图表只接受服务端 ChartSpec；页面不生成 ECharts option，不执行模型生成的 JS。
- 渲染失败、数据不足或类型为 `table` 时降级为表格，并显示原因。

## 验证

本批次已执行：

```bash
cd apps/mp
npm install
npx tsc --noEmit
node validate-mp.js   # 临时校验脚本，检查 JSON、页面/组件文件、WXML 标签、禁用模式与 emoji
```

结果：

- `npx tsc --noEmit`：通过，无输出。
- JSON：19 个 `.json` 全部解析通过。
- 页面：10 个页面均具备 `.ts/.wxml/.wxss/.json`。
- WXML：13 个文件标签闭合检查通过。
- 未发现 `as any`、`@ts-ignore`、`@ts-nocheck`、`# type: ignore` 或 emoji。

尚未执行：

- 微信开发者工具编译、模拟器截图、真机运行与视觉走查。
- 与真实后端完成端到端联调（认证/AI/管理/导出端点仍在并行实现）。
- 图表在低端真机上的 Canvas 2D 性能与字体显示。

## 已知缺口 / 主 agent 需接入

1. 替换 `appid`，配置真实 API 域名与微信 request 合法域名。
2. 认证页（MP16）：B-003/MP-009~011 待实现；当前无登录页，临时用测试脚本写入 `ijd:token`；已批准申请者/电脑端建号用户需要登录入口。
3. 导出契约：`source_type='report'` 与 `source` 描述已由 B08 实现；下载端点返回相对 `download_url`。
4. `PATCH /admin/users/{id}`：微信 `wx.request` 官方类型不含 PATCH，代码保留 PATCH 调用并注明需真机验证；若基础库不支持，需后端提供兼容入口或改用 Web 后台。
5. CSV：小程序不支持预览，当前下载后复制临时链接；需产品确认是否隐藏 CSV 或改为仅 Web 导出。
6. AI 真实链路：`/ai/chat` 已实现（无 Key 时确定性规则 Agent，有 Key 时走 LLM）；网络失败仍保留标注的演示答案。
7. 引用跳转：`citations` 需包含 `region_id` 与 `indicator_id` 或 `indicator_code` 才能跳到指标详情；当前 AI 契约示例只含名称/年份/来源，需后端补齐标识。
8. TDesign 仅列入依赖，未在页面中导入；如后续使用需在开发者工具执行“构建 npm”。
9. `project.private.config.json` 由 DevTools 生成，已在根 `.gitignore` 与 `apps/mp/.gitignore` 忽略，不提交。

## 边界

- 只放小程序代码；不放后台/后端。
- 不直连数据库或 LLM；不保存 Key/AppSecret/JWT Secret。
- 不写死生产 API 域名；生产地址通过运行配置注入。
- 不把 ECharts option 写进页面；只用 ChartSpec 渲染器。
