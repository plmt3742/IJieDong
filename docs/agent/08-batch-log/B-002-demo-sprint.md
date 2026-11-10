# B-002 · 11.12 初步 Demo 冲刺

## 1. 批次信息

| 项 | 内容 |
|---|---|
| 批次 ID | B-002 |
| 日期 | 2026-11-06 ~ 2026-11-12 |
| 操作者 | 人 + agent |
| 状态 | DOING |
| 关联任务 | DOC-017~032、SH-001、BE-001/002、DATA-001~007、MP-001~004、FE-001~003、AI-001~006、QA-001 |
| 关联 ADR | ADR-001、ADR-002、ADR-003、ADR-005 |
| 分支/PR | `main` 已推送（初始 `01e22ec`；最新提交见 `git log`） |

## 2. 目标

11.12 前交付：可运行的初步 demo（导入 → 原生小程序浏览 → 指标图表 → DeepSeek 问答）+ 更新的技术文档 + 开发必要支出评估。

## 3. 输入与上下文

- `15-demo-plan-1112.md`：范围/排期/验收/砍范围。
- `13-tech-stack-review.md`：原生小程序 + 其他栈复审。
- `14-llm-deployment.md`：DeepSeek API + 私有化对比。
- `16-cost-estimate.md`：成本口径。
- `05-architecture.md`：数据模型/API/Agent/ChartSpec。

## 4. 范围

- 数据：SQLite + 区域/指标/数据值 + Excel 导入/演示数据。
- 后端：FastAPI + `/health` + 查询 API + AI 问答。
- 小程序：原生微信小程序首页/区域/指标/图表/问答。
- 后台：最小登录 + 数据列表 + 导入（可简化）。
- 文档：技术栈/LLM/demo/成本/对接文案。
- 运行：本地进程；不强制 Docker。

## 5. 非目标

- 粤政易 SSO/工作台接入。
- 地图/大屏/导出/多年趋势。
- 完整 RBAC/审核/多用户。
- Docker/PostgreSQL 生产部署（11.12 后）。
- 完整测试/压测/等保/信创。

## 6. 验收标准

- [ ] 后端可启动；`/health` 200。
- [ ] 原始模板/演示数据可导入；区域/指标/数据量与模板一致。
- [ ] 微信开发者工具可打开小程序；首页→区域→指标→图表可走通。
- [ ] 至少 3 个 AI 问题可答；答案带引用；无数据会说明。
- [ ] 后台可登录/看数据/触发导入（或命令行导入）。
- [ ] `13`~`19` 文档更新；`16-cost-estimate.md` 有 demo/生产/合规三档；页面地图可点击/导出。
- [ ] 无密钥入库；演示数据标注“演示”。

## 7. 执行计划

| 日期 | 目标 |
|---|---|
| 11.06 | 脚手架：monorepo、FastAPI + SQLite、原生小程序空壳、后台空壳 |
| 11.07 | 数据模型/迁移/种子/Excel 导入/查询 API |
| 11.08 | 小程序首页/区域/指标；request 封装 |
| 11.09 | 图表（柱/表）+ 后台最小 |
| 11.10 | DeepSeek + 工具 + 问答页 |
| 11.11 | 联调/修 bug/文档/成本 |
| 11.12 | 缓冲/彩排/交付 |

### 7.1 子代理工作包

详细文件归属与提示词见 [20-b002-delegation-plan.md](../20-b002-delegation-plan.md)。

| 工作包 | 覆盖 | 状态 |
|---|---|---|
| WP-BE1 | FastAPI + SQLite + health + tests | TODO |
| WP-DATA1 | 模型/迁移/种子/导入/查询 API | TODO |
| WP-MP1 | 原生小程序首页/区域/指标/图表 | TODO |
| WP-ADMIN1 | 后台登录/列表/导入 | TODO |
| WP-AI1 | DeepSeek/工具/ChartSpec/问答 API | TODO |
| WP-INT1 | 主 agent 集成/验收/文档 | TODO |

## 8. 执行记录

> 待执行；按 `B-000-template.md` 的格式补充。

| 时间 | 动作 | 文件/命令 | 结果 |
|---|---|---|---|
| 2026-11-06 | 技术栈复审/LLM 方案/11.12 计划/成本/对接文案 | `13`~`17`、`ADR-005` | DONE；等待确认后开始代码 |
| 2026-11-06 | 三类工作流 | `18-workflows.md` | DONE |
| 2026-11-06 | 有来源的费用调研 | `19-cost-research.md`、`16-cost-estimate.md` | DONE |
| 2026-11-06 | 目录骨架 | `apps/`、`services/`、`packages/` 等 `.gitkeep` | DONE |
| 2026-11-06 | 页面结构地图 | `docs/product/05-page-structure.md`、`ue/page-map.html`、`ue/wireframes.html`、18 页线框 | DONE；地图与线框总览均验证通过 |
| 2026-11-10 | 开发准则修订（DOC-028）：强制规划并委派 subagent、质量优先；取消单独领导模式 | `AGENTS.md`、`README.md`、`docs/README.md`、`docs/agent/{README,01-project,02-goals,04-tasks,07-workflow,11-handoff,18-workflows,20-b002-delegation-plan}.md`、`docs/product/01-prd-lite.md`、本记录 | 文档已更新；diff/链接/无 emoji 检查通过（主 agent 复跑） |
| 2026-11-10 | 记录 11.12 用户决策（数据、登录/申请、数据类型、demo 形态、角色、导出、视觉），完成契约文档起草与主 agent 一致性审查 | `12-open-questions.md` §0.3、`15-demo-plan-1112.md` §11、`04-tasks.md` §2.1、`11-handoff.md`、`21`~`25`、`product/06`、`product/07`、本记录 | DOC-029~032 DONE；契约文档 21/22、23、06、24/07/25 已完成；diff/链接/无 emoji 检查通过（主 agent 复跑） |
| 2026-11-10 | B00 FastAPI + SQLite session 脚手架 | `services/api/**` | DONE；`python -m pytest -q` 5 passed；`/health` 200；`/ready` 200；commit `b943aa8` |
| 2026-11-10 | B01 数据模型 + Alembic 初始迁移 | `services/api/app/models/**`、`alembic/**`、`tests/unit/test_models.py`、`test_migrations.py` | DONE；12 张表；`pytest` 12 passed；`alembic upgrade/downgrade` 通过；`alembic check` 无差异；commit `111914a` |
| 2026-11-10 | B02 确定性合成种子 | `services/api/scripts/**`、`tests/unit/test_seed_demo.py` | DONE；227 区域/15 指标/1608 值；42 缺失；454 文本；`pytest` 20 passed；commit `52d0adb` |
| 2026-11-10 | B04 只读查询 API | `services/api/app/schemas/**`、`app/services/query_service.py`、`app/api/v1/**`、`tests/api/**`、`contracts/openapi.json` | DONE；区域/指标/数据值/排名/对比/总览；`pytest` 36 passed；OpenAPI 14 paths；commit `29dfe61` |
| 2026-11-10 | 上下文保护收口 | `11-handoff.md`、本记录 | B00~B04 完成；C/D/E 待续；下一步 C01/C02 |
| | | | |

## 9. 风险与阻塞

| 风险 | 缓解 |
|---|---|
| 范围失控/质量问题 | 按 `15-demo-plan-1112.md` §11 的 Demo v0 范围与原子任务推进；未完成功能隐藏 |
| 原生小程序图表包体/兼容 | echarts-for-weixin 自定义构建；表格降级 |
| 真实数据/Key/AppID 未到 | 演示数据 + mock/预生成答案 + 测试号 |
| 需求临时加范围 | 记录到 `12-open-questions.md`，不纳入 11.12 |

## 10. 验证证据（文档 + 后端阶段）

| 验证项 | 命令/方式 | 结果 |
|---|---|---|
| 页面地图冒烟 | `python -X utf8 docs/product/ue/verify_map.py` | 18 页面 / 29 边；详情/跳转/模块/搜索/缩放/页面图/UE 标注图均通过；console errors 0 |
| 线框总览冒烟 | `python -X utf8 docs/product/ue/verify_wireframes.py` | 18 卡片 / 18 地图链接；console errors 0 |
| 文档内链 | `python scripts/check-links.py` | 41 个 Markdown 文件，全部相对链接可解析 |
| 本地目录 ignore | `git check-ignore -v Resource learning tools .obsidian .omo` | 均命中 `.gitignore` |
| 目录骨架 | `dir /s /b apps services packages` | 40 个 `.gitkeep` 占位；与 `06-file-tree.md` 一致 |
| 费用来源 | `19-cost-research.md` | 官方/政府采购/云厂商/转载来源已标注；价格有日期/地区 |
| 后端 B00~B05 + B08 | `pytest`、Alembic、seed、API smoke | `pytest` 119 passed；迁移 0001/0002/0003 升级/回滚/`check` 通过；种子 227/15/1608；OpenAPI 35 paths |
| Web 后台 | `pnpm build`、headless Edge 走查 | 登录/总览/数据/导入/申请/用户/审计可打开；build 通过 |
| 原生小程序 | `npm run typecheck`、JSON/WXML 校验 | 10 页/3 组件；typecheck 通过；DevTools/真机未安装 |
| AI/导出 smoke | TestClient | AI 三例 + no_data；CSV/XLSX/PNG/PDF 均 ready 且下载 200 |
| 小程序/DeepSeek 真机 | 微信开发者工具/真实 Key 调用 | 尚未执行，不能标记 DONE |

## 11. 下一步

1. 继续 B-002：主 agent 审查/集成契约文档（DOC-029~032），随后开始数据底座与三端实现。
2. 每完成一天更新本记录和 `04-tasks.md`。
3. 11.12 交付后写复盘，进入 B-003。

## 12. 2026-11-10 六步推进

> 目标：按“契约收口 → 认证/后台 → 小程序 → AI/导出 → 种子/部署 → 文档同步”推进 Demo v0。

### Step 1 契约收口（DONE）

| 动作 | 文件 | 结果 |
|---|---|---|
| 开发区编码改为 `JD-Z-01`/`JD-Z-02`，行政镇街保持 `JD-T-01`~`JD-T-13` | `services/api/scripts/build_region_fixture.py`、`scripts/fixtures/regions_2025.json` | 227 区域重新生成；13 行政镇街 + 2 开发区 |
| 区域列表增加 `category`，分页默认 20、最大 100 | `app/api/v1/regions.py`、`app/services/query_service.py` | 与 05/21/22 一致 |
| 指标列表增加 `value_type` | `app/api/v1/indicators.py`、`app/services/query_service.py` | 文本指标可筛出 2 个 |
| 数据值列表增加 `quality_status`，公开接口只读 `published`，分页默认 20、最大 100 | `app/api/v1/data.py`、`app/services/query_service.py` | 与 05/21/22 一致 |
| 总览增加 `coverage` | `app/schemas/dashboard.py`、`app/services/query_service.py` | 区级 13 个数值指标覆盖率 100.0 |
| 新增 OpenAPI 导出脚本并重新生成契约 | `services/api/scripts/export_openapi.py`、`contracts/openapi.json` | 14 paths、27 schemas；新参数与 coverage 已写入 |
| 文档同步 | `05-architecture.md`、`21-technical-architecture-v2.md`、`22-data-integration-spec.md` | 明确 Demo v0 用 `period_year`/`root_code`；12 张表；错误码补齐 |

验证：`python -m pytest -q` -> 40 passed；`python -m compileall -q app tests` 通过；`contracts/openapi.json` 14 paths。

### Step 5 部署资产（部分完成）

- 新增 `deploy/docker-compose.yml`、`docker-compose.dev.yml`、`nginx.conf`、`.env.example`、`scripts/backup.sh`、`scripts/restore.sh`。
- 新增 `services/api/Dockerfile`、`.dockerignore`、`.github/workflows/ci.yml`。
- SQLite 连接启用 `PRAGMA foreign_keys=ON`、`busy_timeout=5000`、文件库 WAL；新增 `tests/unit/test_db_session.py`。

### Step 2 认证/后台（DONE）

| 动作 | 文件 | 结果 |
|---|---|---|
| 认证/JWT/密码哈希/RBAC | `app/core/security.py`、`app/schemas/auth.py`、`app/services/auth_service.py`、`app/api/v1/auth.py` | 登录/me/申请/状态/退出/改密 6 端点 |
| 申请审批/用户/审计 | `app/schemas/admin.py`、`app/services/audit_service.py`、`app/api/v1/admin.py` | 列表/批准/驳回/用户/审计 6 端点 |
| Excel 导入 | `app/services/import_service.py` | 上传/批次/错误报告 4 端点；atomic/partial；空值=missing |
| 迁移 | `alembic/versions/0002_auth_and_admin.py` | users.phone unique/token_version；申请隐私/提交元数据；import source_id |
| Web 后台 | `apps/admin/**` | 登录/总览/数据/导入/申请/用户/审计；`pnpm build` 通过；真实浏览器走查 |

验证：`pytest` 80 passed；`compileall` 通过；OpenAPI 29 paths；`pnpm build` 通过；管理员批准流程在 headless Edge 中走通。

### Step 3 小程序（DONE，DevTools 待验证）

- 10 页：home/regions/region-detail/indicator-detail/ai/chat/profile/apply/admin-approval/export。
- 3 组件：ChartSpec Canvas 2D、metric-card、state-view。
- `npm run typecheck` 通过；JSON 19 个、页面 10 个、WXML 13 个结构校验通过。
- 微信开发者工具/真机未安装，视觉与端到端未验证。

### Step 5 种子/部署（DONE，资产）

- 数据库已播种：227 区域/15 指标/1608 值/454 文本/42 缺失。
- SQLite `PRAGMA foreign_keys=ON`、`busy_timeout=5000`、文件库 WAL；`test_db_session.py` 通过。
- `requirements.txt` 增加 asyncpg、psycopg、xlrd、openpyxl、python-multipart、playwright。
- 根 `package.json` + `pnpm-workspace.yaml`；`apps/admin` 与 `packages/*` 纳入 workspace。
- `.github/workflows/ci.yml`：docs/api/web/mp 四个 job。
- `deploy/`：Compose、Nginx、Dockerfile、备份/恢复脚本。

### Step 4 AI/导出（DONE）

- `/api/v1/ai/chat`：确定性规则 Agent（无 Key）+ OpenAI 兼容 LLM 通道（有 Key）；AnswerBlocks/引用/无数据拒答/会话落库。
- 10 个只读工具；五层校验；限流 10/min/用户、5/day/游客 IP。
- `POST/GET /api/v1/exports` + download：PNG/PDF/XLSX/CSV；migration 0003；同步生成 ready。
- 验证：119 tests passed；OpenAPI 35 paths；AI 三例（云路镇 31038、镇街排名、曲溪/云路对比）与导出四格式 smoke 通过。
- 真实 DeepSeek Key 本地联调通过：`deepseek-chat`、`degraded=false`；Key 只写 `services/api/.env`（gitignored），未进入仓库。

### Step 6 文档收口（DONE）

- 00/01/03/04/05/06/07/09/11/12/15/18/20/21/22/23/24/25 与批次记录已同步。
- `contracts/openapi.json` 已重新导出为 35 paths / 83 schemas；`contracts/README.md`、根 README、服务 README、后台/小程序 README 已同步。
- 全量复跑：pytest 119 passed、compileall、Alembic、Web build、小程序 typecheck、docs checks 全部通过。
