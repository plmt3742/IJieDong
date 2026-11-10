---
owner: 项目开发者
last_updated: 2026-11-10
status: DOING
read_when: 接续小程序登录、页面地图 v2、双端视觉对齐任务时
---

# B-003 · 小程序登录与双端视觉对齐

> 目标：修掉“申请通过/电脑端建号后小程序没有登录入口”的功能缺口；把页面地图升级为能看清关系、数据流、触发事件和相对位置的 v2；随后统一小程序与 Web 的视觉和按钮秩序。

## 1. 当前状态（2026-11-10）

- 后端：B00~B05 + B08 已完成；119 tests；OpenAPI 35 paths；migration 0001/0002/0003；数据库已播种 227/15/1608/42。
- Web 后台：登录/总览/数据/导入/申请/用户/审计已可运行；`pnpm build` 通过。
- 小程序：10 页 + 3 组件；`tsc --noEmit` 通过；AppID `wx8f2e6e70d602cee9` 已配置；Preview 581.2 KB。
- AI/导出：真实 DeepSeek Key 已本地联调（`deepseek-chat`、`degraded=false`）；PNG/PDF/XLSX/CSV 可生成。
- 部署：**本机 Windows 工作站作为服务器**，API/Web 监听 `0.0.0.0`；局域网 `http://10.62.172.85:5173/`；防火墙仅放行 LocalSubnet 8000/5173。
- 图标：96/144/192/512/1024 PNG + SVG 已生成并提交（`6d8c9a5`）。
- Git：`feat/b002-demo-v0` 已推送；最新提交 `c40acf0`（LAN 配置）；工作区干净。

## 2. 必须修复的问题

1. **小程序没有登录页/登录入口**：申请通过的用户、电脑端批量建号的用户，无法在小程序输入账号密码登录。
2. **申请通过后无引导**：MP14 状态页只展示“已批准”，没有“去登录”；MP08 只有退出，没有登录/切换账号。
3. **首次改密未闭环**：后端 `must_change_password` 与 `POST /auth/change-password` 已有，前端没有入口；批准返回的初始密码由管理员一次性展示，用户需要知道用它登录并改密。
4. **页面地图过期**：当前 `page-map.html` 是 v1（18 页/29 跳转，基于 05），不含 MP09–MP16、AD10–AD13、登录/申请/导出/管理真实页面；页面关系、数据流、触发事件和相对位置不足。
5. **双端视觉不统一**：小程序与 Web 的颜色、字号、间距、圆角、状态标签、按钮层级/排列没有共享规范；部分页面按钮排列缺少主次与顺序。

## 3. 工作包

### WP-AUTH-MP（P0，先做）

**目标**：小程序有可用登录入口，覆盖“申请已批准”和“电脑端建号”两类账号。

**范围**：

- 新增 `apps/mp/miniprogram/pages/login/`（MP16 账号登录），注册到 `app.json`。
- MP08 增加“登录 / 切换账号”；MP14 在 approved 状态增加“去登录”；游客/申请者可见登录入口。
- 登录字段：用户名或手机号 + 密码；`POST /auth/login`；成功后存 token/user，按角色进入 MP01 或来源页。
- 首次登录提示改密；接入 `POST /auth/change-password`；`must_change_password` 为 true 时引导改密（后端强制拦截可作为后续小任务）。
- 401/`USER_DISABLED` 清理 token 并回游客态；退出登录已有逻辑复用。
- 管理员/审批者登录后 MP08 显示 MP15 管理入口。
- 更新 `services/api.ts`、`types/api.ts`、`utils/auth.ts`、`app.json`、相关页面 WXML/WXSS。

**验收**：

- 用 Web 后台批准一个申请，拿到手机号 + 初始密码，在小程序 MP16 登录成功并进入 MP01。
- 用 Web 后台创建的用户名/密码，在小程序 MP16 登录成功。
- 错误密码不泄露账号是否存在；禁用账号提示；退出/401 后回游客。
- 管理员登录后能看到 MP15；普通 viewer 看不到。
- 微信开发者工具模拟器通过；真机 Preview 至少在局域网可用（HTTP 域名校验限制需在批次记录写明）。

### WP-UE-MAP（P0，可与 WP-AUTH-MP 并行）

**目标**：生成页面地图 v2，覆盖 29 页（MP01–MP16、AD01–AD13），能看清关系、数据流、触发事件和相对位置。

**必须呈现**：

- **相对位置**：按用户旅程/角色分层，而不是简单网格。建议 X 轴为“入口/身份 → 浏览 → 指标/AI → 导出/账号 → 管理”，Y 轴为设备/角色泳道（MP、AD；游客/查看者/管理员）。
- **页面关系**：导航边（实线）、返回边、条件边（仅管理员/仅登录）；边上标注触发动作。
- **数据流**：页面 ↔ API ↔ 数据表/服务（`data_values`、`/ai/chat`、`/auth/*`、`/exports`、导入批次）用不同线型/颜色；不要把所有数据流画成同一种箭头。
- **触发事件**：点击、提交、批准、驳回、导入、导出、401、状态变更等以标签/徽标出现在边上或节点详情。
- **交互**：搜索、设备/优先级/角色/边类型筛选、点击节点看详情（页面/入口/数据/事件/API）、高亮相邻节点、缩放/平移/复位、缩略图/全览、导出 PNG。
- **观看体验**：默认全览可读；长页面名换行；边不穿过节点；颜色克制；桌面 1440 和 1024 可用；无 console error。
- **产物**：更新或新增 `page-map.html`（保持原链接可用，或提供 v2 并在 README 标注）；更新 `ue-spec.json` 到 29 页；新增可重复运行的生成脚本（建议 `build_page_map.py`，不要依赖仓库外技能脚本）；更新 `wireframes.html` 或明确 v2 只做地图不做 29 张线框。
- **文档**：`docs/product/06-page-design-v2.md` 是页面事实源；`05-page-structure.md` 标注“历史 v1”；`ue/README.md` 更新产物/重新生成/验证记录。

**验收**：

- 29 个页面、至少 40 条边（导航+数据+事件；以实际统计为准），节点和边都有可读标签。
- 能从 MP16 登录 → MP01 → MP04 → MP12 → MP14 走通；从 AD05 导入 → AD03/MP01 看到数据流。
- 筛选/搜索/详情/缩放/复位/导出 PNG 通过 Playwright 冒烟；console errors 0。
- 1024 宽度下详情面板不遮挡主图；长中文页面名不溢出。

### WP-MP-UI（P0，WP-AUTH-MP 后）

**目标**：深入优化小程序 11 个页面（MP01–MP08、MP12、MP14、MP15、MP16），统一视觉与按钮秩序。

**范围**：

- 统一页面骨架：顶部标题/返回、内容区、底部操作区、安全区、loading/empty/error/locked/no-permission 状态。
- 统一卡片、指标、标签、列表、表单、弹窗、图表容器、引用块、notice/actions。
- 按钮层级：主按钮、次按钮、文字按钮、危险按钮；移动端底部主操作全宽/右对齐规则；同页按钮不超过 3 个并列。
- 首页/区域/指标/AI/我的/申请/登录/导出/管理逐页走查：信息层级、间距、点击区域、长文本、空状态、弱网。
- 避免“每页一套样式”；复用 `app.wxss` 与共享组件，必要时新增 `components/`。

**验收**：

- 11 页在 375px 宽度下无横向滚动；主操作在首屏可见；按钮主次清晰。
- 登录/申请/导出/AI 四条主路径连续走通。
- 开发者工具截图或录屏归档；真机至少完成一次 Preview 走查。

### WP-WEB-UI（P0，与 WP-MP-UI 共用 token）

**目标**：Web 后台与小程序视觉对齐，按钮排列有秩序。

**范围**：

- 建立双端共享设计 token 表：颜色、字号、行高、间距、圆角、边框、阴影、状态色、按钮尺寸。
- Web `src/styles/tokens.css`/`element.css` 与 MP `app.wxss` 使用同一组语义变量；允许平台差异（Element Plus 组件尺寸），但不允许语义色/字号/间距各自为政。
- 统一按钮顺序：弹窗/抽屉底部“取消在左、主操作在右”；移动端主操作在底部全宽；危险操作与主操作分离；列表行操作不超过 2 个直接按钮，其余进“更多”。
- 审计 AD01–AD08 的筛选区/表格/抽屉/弹窗/状态标签，修正按钮拥挤、主次不清、间距不齐。
- 出一份 `docs/product/08-visual-alignment.md`（或并入 06/07）：token 表、按钮层级、页面栅格、状态规范、双端对照。

**验收**：

- Web 1440/1024 与 MP 375 截图对照，颜色/字号/间距/状态标签一致或有明确平台差异说明。
- 所有弹窗/抽屉按钮顺序统一；列表行操作不超过 2 个直接按钮。
- `pnpm build` 通过；无新增 UI 框架。

### WP-QA-DOCS（P0，最后）

- 后端：`pytest` 119+、compileall、Alembic、seed check。
- Web：`pnpm build`、登录→总览→数据→导入→审批→审计走查。
- 小程序：`tsc --noEmit`、JSON/WXML 校验、DevTools/Preview 主路径。
- 页面地图：Playwright 冒烟、console errors 0、导出 PNG。
- 文档：00/03/04/06/08/11/UE README/本记录同步；无 emoji、链接检查通过。
- 更新 `11-handoff.md` 当前快照与下一步；更新 `08-batch-log/README.md` 索引。

## 4. 顺序与依赖

```text
WP-AUTH-MP（先）
   ↓
WP-MP-UI ──→ WP-WEB-UI（共用 token）──→ WP-QA-DOCS
   ↑
WP-UE-MAP（可并行；页面事实源用 06）
```

## 5. 文件归属

| 区域 | 归属 |
|---|---|
| `apps/mp/miniprogram/pages/login/**`、profile/apply 修改 | WP-AUTH-MP |
| `apps/mp/miniprogram/app.json`、`services/api.ts`、`types/api.ts`、`utils/auth.ts` | WP-AUTH-MP（共享文件由主 agent 复核） |
| `apps/mp/miniprogram/**` 视觉 | WP-MP-UI |
| `apps/admin/src/styles/**`、components/views | WP-WEB-UI |
| `docs/product/ue/**`、`06`、`05` 标注、`08-visual-alignment.md` | WP-UE-MAP / WP-WEB-UI |
| `docs/agent/00/03/04/08/11` | WP-QA-DOCS / 主 agent |

## 6. 风险与边界

- **微信域名校验**：本机 HTTP + 局域网 IP 在开发者工具可关闭校验；真机 Preview 若仍拦截，需要 HTTPS 隧道/域名，不在本批次硬扛。
- **初始密码分发**：批准时 Web 后台一次性展示初始密码；小程序无法自动收到。演示流程需管理员把手机号+初始密码给申请者；后续可做短信/首次设置密码。
- **后端强制改密**：当前 `must_change_password` 未在 API 层强制；本批次先做前端提示，后端强制作为后续小任务。
- **页面地图**：不要继续依赖仓库外 `render_map.py`；必须在仓库内可重复生成。
- **资源**：本机 2C2G 云服务器不用于本批次；本机服务器继续使用，避免同时跑云部署。
- **不提交**：`.env`、JWT Secret、DeepSeek Key、真实手机号/密码；AppID 可提交。

## 7. 交接提示词（新会话复制）

```text
你是 i揭东项目的开发 agent。先读：
1. AGENTS.md
2. docs/agent/00-context.md
3. docs/agent/04-tasks.md
4. docs/agent/11-handoff.md
5. docs/agent/08-batch-log/B-003-ui-auth-alignment.md
6. docs/product/06-page-design-v2.md（页面事实源）
7. docs/product/ue/README.md（v1 已过时）
8. docs/agent/05-architecture.md 的认证/API/权限节

当前批次：B-003 小程序登录与双端视觉对齐。
范围：apps/mp 登录入口与页面优化；docs/product/ue 页面地图 v2；apps/admin 与 MP 视觉对齐；不接云服务器。
不做：粤政易 SSO、真实数据接入、后端大改、云部署。
验收：MP16 登录两类账号；页面地图 29 页/关系+数据流+事件+相对位置；双端 token/按钮秩序一致；119+ tests、Web build、MP typecheck、页面地图冒烟通过。
先复述任务与计划，再按 WP-AUTH-MP → WP-UE-MAP/WP-MP-UI → WP-WEB-UI → WP-QA-DOCS 推进。
```

## 8. 验证命令

```bash
# 后端
cd services/api
python -m pytest -q
python -m compileall -q app tests scripts
python -m alembic -c alembic.ini upgrade head
python scripts/seed_demo.py --check

# Web
cd <repo-root>
pnpm install --frozen-lockfile
pnpm build:admin

# 小程序
npm --prefix apps/mp run typecheck

# 页面地图（v2 完成后）
python -X utf8 docs/product/ue/verify_map.py

# 文档
python scripts/check-links.py
python -X utf8 scripts/check-no-emoji.py
```
