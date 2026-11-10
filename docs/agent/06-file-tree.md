---
owner: 项目开发者
last_updated: 2026-11-10
status: active
read_when: 新建文件/目录前；review 目录结构时；不确定文件放哪时
---

# 06 · 文件树与目录职责

## 1. 当前实际结构（2026-11-10）

```text
IJieDong/
├── AGENTS.md
├── README.md
├── .gitignore
├── .editorconfig
├── .gitattributes
├── Resource/                       # 本地只读资料，gitignore
│   ├── Integration Materials/
│   └── Preliminary Plan and Project Content/
├── docs/
│   ├── README.md
│   ├── agent/
│   │   ├── README.md
│   │   ├── 00-context.md
│   │   ├── 01-project.md
│   │   ├── 02-goals.md
│   │   ├── 03-roadmap.md
│   │   ├── 04-tasks.md
│   │   ├── 05-architecture.md
│   │   ├── 06-file-tree.md
│   │   ├── 07-workflow.md
│   │   ├── 08-batch-log/
│   │   │   ├── README.md
│   │   │   ├── B-000-template.md
│   │   │   ├── B-001-project-init.md
│   │   │   └── B-002-demo-sprint.md
│   │   ├── 09-risks.md
│   │   ├── 10-resources.md
│   │   ├── 11-handoff.md
│   │   ├── 12-open-questions.md
│   │   ├── 13-tech-stack-review.md
│   │   ├── 14-llm-deployment.md
│   │   ├── 15-demo-plan-1112.md
│   │   ├── 16-cost-estimate.md
│   │   ├── 17-outreach-copy.md
│   │   ├── 18-workflows.md
│   │   ├── 19-cost-research.md
│   │   ├── 20-b002-delegation-plan.md
│   │   ├── 21-technical-architecture-v2.md
│   │   ├── 22-data-integration-spec.md
│   │   ├── 23-auth-and-application-spec.md
│   │   ├── 24-ai-and-component-spec.md
│   │   └── 25-export-spec.md
│   ├── product/
│   │   ├── README.md
│   │   ├── 01-prd-lite.md
│   │   ├── 02-ia-and-flows.md
│   │   ├── 03-page-specs.md
│   │   ├── 04-data-catalog.md
│   │   ├── 05-page-structure.md
│   │   ├── 06-page-design-v2.md
│   │   ├── 07-component-library-spec.md
│   │   └── ue/
│   │       ├── README.md
│   │       ├── page-map.html
│   │       ├── wireframes.html
│   │       ├── ue-spec.json
│   │       ├── build_ue.py
│   │       ├── verify_map.py
│   │       ├── verify_wireframes.py
│   │       ├── screens/           # 18 页线框 + PNG
│   │       └── verification/      # 冒烟/导出样例
│   └── adr/
│       ├── README.md
│       ├── ADR-000-template.md
│       ├── ADR-001-tech-stack.md
│       ├── ADR-002-data-model.md
│       ├── ADR-003-agent-architecture.md
│       ├── ADR-004-deployment-and-compliance.md
│       └── ADR-005-native-wechat-miniprogram.md
├── apps/
│   ├── admin/README.md             # B-002 脚手架占位
│   └── mp/README.md                # B-002 脚手架占位
├── services/
│   └── api/README.md               # B00~B04 可运行后端
├── packages/
│   ├── contracts/README.md         # B-002 占位
│   └── chart-spec/README.md        # B-002 占位
├── contracts/
│   └── README.md                   # OpenAPI 已生成 B04 查询端点
├── deploy/
│   └── README.md                   # 部署占位
├── scripts/
│   └── README.md                   # 跨端脚本占位
├── learning/                       # 本地学习笔记，gitignore
├── tools/                          # 本地工具，gitignore
└── .obsidian/                      # 本地 Obsidian 配置，gitignore
```

> `Resource/`、`learning/`、`tools/`、`.obsidian/`、`.omo/` 不进 Git；不要在这些目录里写产品代码。

### 1.1 B-002 已创建的目录骨架（2026-11-10）

以下目录已实际创建（空目录用 `.gitkeep` 占位），后续按任务填内容：

| 端 | 已创建目录 |
|---|---|
| 后台 | `apps/admin/src/{api,assets,components,composables,layouts,router,stores,styles,types,utils,views}`、`tests/`、`e2e/` |
| 小程序 | `apps/mp/miniprogram/{pages,components,services,utils,types,images,styles}`、`apps/mp/typings/` |
| 后端 | `services/api/app/{core,db,models,schemas,api/v1,services,ai,utils}`、`alembic/versions/`、`tests/{unit,api,fixtures}/`、`scripts/` |
| 共享 | `packages/contracts/src/`、`packages/chart-spec/src/` |
| 契约 | `contracts/openapi/`、`contracts/examples/` |
| 部署 | `deploy/scripts/` |
| 设计 | `docs/product/ue/`（`screens/`、`page-map.html`、`ue-spec.json`、`verification/`） |

## 2. 目标文件树（B-002 之后）

```text
IJieDong/
├── AGENTS.md
├── README.md
├── .gitignore
├── .editorconfig
├── .gitattributes
├── pnpm-workspace.yaml            # Node workspace
├── package.json                   # 根脚本（lint/test/build 编排）
├── docs/
│   ├── README.md
│   ├── agent/                     # agent 工程上下文（只放文档）
│   ├── product/                   # 产品/交互/页面/数据目录
│   └── adr/                       # 架构决策
├── apps/
│   ├── admin/                     # Web 管理后台（Vue3）
│   │   ├── package.json
│   │   ├── vite.config.ts
│   │   ├── tsconfig.json
│   │   ├── index.html
│   │   ├── .env.example
│   │   ├── src/
│   │   │   ├── main.ts
│   │   │   ├── App.vue
│   │   │   ├── api/               # HTTP client、端点、类型
│   │   │   ├── assets/
│   │   │   ├── components/        # 通用组件（表格/图表/空错 loading）
│   │   │   ├── composables/       # useAuth/usePagination/useChart
│   │   │   ├── layouts/           # AdminShell
│   │   │   ├── router/
│   │   │   ├── stores/            # Pinia
│   │   │   ├── styles/
│   │   │   ├── types/
│   │   │   ├── utils/
│   │   │   └── views/             # 页面
│   │   ├── tests/                 # Vitest
│   │   └── e2e/                   # Playwright
│   └── mp/                        # 原生微信小程序
│       ├── project.config.json
│       ├── project.private.config.json  # 本地配置，gitignore
│       ├── package.json
│       ├── tsconfig.json
│       ├── .env.example
│       ├── miniprogram/
│       │   ├── app.ts
│       │   ├── app.json
│       │   ├── app.wxss
│       │   ├── sitemap.json
│       │   ├── pages/             # 首页/区域/指标/问答/我的
│       │   ├── components/        # chart/region-card/empty/loading
│       │   ├── services/          # request/api
│       │   ├── utils/
│       │   ├── types/
│       │   ├── images/
│       │   └── styles/
│       └── typings/               # miniprogram-api-typings
├── services/
│   └── api/                       # FastAPI
│       ├── pyproject.toml
│       ├── requirements.txt        # 11.12 过渡（venv/pip）；uv 可选
│       ├── uv.lock                 # 安装 uv 后生成
│       ├── .python-version
│       ├── .env.example
│       ├── alembic.ini
│       ├── alembic/
│       │   ├── env.py
│       │   └── versions/
│       ├── app/
│       │   ├── main.py
│       │   ├── core/              # config/logging/errors/security/request_id
│       │   ├── db/                # engine/session/base
│       │   ├── models/
│       │   ├── schemas/
│       │   ├── api/v1/            # auth/regions/indicators/data/ai/admin/health
│       │   ├── services/          # data/import/auth/audit
│       │   ├── ai/                # client/tools/agent/prompts/chart/validator
│       │   └── utils/
│       ├── tests/
│       │   ├── unit/
│       │   ├── api/
│       │   └── fixtures/
│       ├── scripts/               # seed/import demo
│       └── data/                  # 本地数据（gitignore）
├── packages/
│   ├── contracts/                 # OpenAPI 生成的 TS 类型 + 常量
│   │   ├── package.json
│   │   └── src/
│   └── chart-spec/                # ChartSpec 类型 + ECharts 适配
│       ├── package.json
│       └── src/
├── contracts/
│   ├── openapi.json               # 后端导出，提交仓库
│   ├── examples/                  # 请求/响应示例
│   └── README.md
├── deploy/
│   ├── docker-compose.yml
│   ├── docker-compose.dev.yml
│   ├── nginx.conf
│   ├── .env.example
│   ├── scripts/
│   └── README.md
├── scripts/
│   ├── dev.ps1 / dev.sh
│   ├── export-openapi.sh
│   └── check-links.py
├── .github/
│   └── workflows/
│       └── ci.yml
├── Resource/                      # 本地只读，gitignore
├── learning/                      # 本地学习，gitignore
└── tools/                         # 本地工具，gitignore
```

## 3. 目录职责

| 目录 | 放什么 | 不放什么 |
|---|---|---|
| `docs/agent/` | 工程上下文、任务、架构、风险、交接、批次记录 | 产品原型、代码、临时笔记 |
| `docs/product/` | PRD、IA/流程、页面规范、数据目录 | API 字段细节（放 05）、数据库迁移 |
| `docs/adr/` | 不可逆/跨模块决策 | 日常任务、样式调整 |
| `apps/admin/` | Web 后台代码、后台组件、后台测试 | 小程序代码、后端代码、部署脚本 |
| `apps/mp/` | 原生微信小程序：pages/components/services/配置 | 后台代码、Python 代码、H5（除非后续加壳） |
| `services/api/` | FastAPI 应用、模型、迁移、服务、测试 | 前端代码、原始数据文件 |
| `packages/contracts/` | 共享 TS 类型/常量 | 业务逻辑、页面 |
| `packages/chart-spec/` | ChartSpec 类型、ECharts 适配、渲染工具 | 数据查询、API 调用 |
| `contracts/` | OpenAPI 文件、示例 | 手写 SDK、业务代码 |
| `deploy/` | Compose、Nginx、环境模板、部署脚本 | 业务代码、密钥 |
| `scripts/` | 跨端开发脚本、校验脚本 | 业务逻辑、一次性临时脚本（放 `tools/`） |
| `Resource/` | 原始资料（只读） | 任何生成物、代码、笔记 |
| `learning/` | 学习笔记、实验 | 产品交付物 |
| `tools/` | 本地工具/脚本 | 需要进 CI 的代码 |

## 4. 命名规范

| 类型 | 规则 | 示例 |
|---|---|---|
| 目录 | kebab-case | `data-values/`、`chart-spec/` |
| Vue 组件 | PascalCase | `RegionPicker.vue`、`ChartCard.vue` |
| TS 工具/模块 | kebab-case | `format-number.ts`、`api-client.ts` |
| Python 模块 | snake_case | `data_service.py`、`import_jobs.py` |
| Python 类 | PascalCase | `DataValueService` |
| 数据库表 | snake_case 复数 | `regions`、`data_values`、`audit_logs` |
| 数据库字段 | snake_case | `period_year`、`value_number` |
| API 路径 | kebab-case，复数资源 | `/data-values`、`/audit-logs` |
| 指标编码 | snake_case | `population_resident`、`gdp` |
| 区域编码 | 大写短横线 | `JD`、`JD-QX`、`JD-QX-001` |
| 环境变量 | 大写下划线 | `DATABASE_URL`、`LLM_API_KEY` |
| 文档 | 数字前缀 + kebab-case | `05-architecture.md` |
| 批次记录 | `B-三位编号-slug.md` | `B-002-scaffold.md` |

## 5. 文件放置决策树

```text
新文件要放哪？
├─ 是原始资料/需求文档？ → Resource/（只读，gitignore）
├─ 是学习笔记/实验？ → learning/（gitignore）
├─ 是本地工具/一次性脚本？ → tools/（gitignore）
├─ 是 agent 上下文/任务/架构/风险/交接？ → docs/agent/
├─ 是 PRD/IA/页面规范/数据目录？ → docs/product/
├─ 是不可逆技术决策？ → docs/adr/
├─ 是 Web 后台页面/组件？ → apps/admin/src/
├─ 是原生微信小程序页面/组件？ → apps/mp/miniprogram/
├─ 是后端模型/接口/服务？ → services/api/app/
├─ 是数据库迁移？ → services/api/alembic/versions/
├─ 是前后端共享 TS 类型？ → packages/contracts/
├─ 是 ChartSpec/图表适配？ → packages/chart-spec/
├─ 是 OpenAPI/示例？ → contracts/
├─ 是部署/Compose/Nginx？ → deploy/
├─ 是跨端脚本/CI 辅助？ → scripts/
└─ 以上都不是？ → 先停，改 06 文档并说明理由，再新建目录
```

## 6. 禁止事项

- 不在 `Resource/` 写任何文件；不修改原始 doc/xls/rar。
- 不在根目录堆 `test.py`、`temp.ts`、`笔记.md` 等临时文件。
- 不把数据文件（`.xls`、`.db`、`.csv` 大文件）提交到仓库；演示数据用脚本生成或放 `fixtures/` 小样本。
- 不把 API Key、AppSecret、数据库密码写入代码、文档、示例、日志。
- 不新增顶层目录（如 `src/`、`server/`、`web/`）而不更新本文件。
- 不把后端代码放进 `apps/`，不把前端代码放进 `services/`。

## 7. 新增顶层目录的流程

1. 在 `06-file-tree.md` 增加目录、职责、放置规则。
2. 在批次记录里说明为什么现有目录不行。
3. 更新 `README.md` 的目录结构。
4. 再创建目录/文件。

> 单人项目也要走这个流程；否则三个月后自己也不认识仓库。
