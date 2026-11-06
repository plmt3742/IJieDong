# B-002 · 11.12 初步 Demo 冲刺

## 1. 批次信息

| 项 | 内容 |
|---|---|
| 批次 ID | B-002 |
| 日期 | 2026-11-06 ~ 2026-11-12 |
| 操作者 | 人 + agent |
| 状态 | DOING |
| 关联任务 | DOC-017~027、SH-001、BE-001/002、DATA-001~007、MP-001~004、FE-001~003、AI-001~006、QA-001 |
| 关联 ADR | ADR-001、ADR-002、ADR-003、ADR-005 |
| 分支/PR | 待创建 |

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

## 8. 执行记录

> 待执行；按 `B-000-template.md` 的格式补充。

| 时间 | 动作 | 文件/命令 | 结果 |
|---|---|---|---|
| 2026-11-06 | 技术栈复审/LLM 方案/11.12 计划/成本/对接文案 | `13`~`17`、`ADR-005` | DONE；等待确认后开始代码 |
| 2026-11-06 | 三类工作流 | `18-workflows.md` | DONE |
| 2026-11-06 | 有来源的费用调研 | `19-cost-research.md`、`16-cost-estimate.md` | DONE |
| 2026-11-06 | 目录骨架 | `apps/`、`services/`、`packages/` 等 `.gitkeep` | DONE |
| 2026-11-06 | 页面结构地图 | `docs/product/05-page-structure.md`、`ue/page-map.html`、`ue/wireframes.html`、18 页线框 | DONE；地图与线框总览均验证通过 |
| | | | |

## 9. 风险与阻塞

| 风险 | 缓解 |
|---|---|
| 6 天太紧 | 按 `15-demo-plan-1112.md` §7 砍范围 |
| 原生小程序图表包体/兼容 | echarts-for-weixin 自定义构建；表格降级 |
| 真实数据/Key/AppID 未到 | 演示数据 + mock/预生成答案 + 测试号 |
| 需求临时加范围 | 记录到 `12-open-questions.md`，不纳入 11.12 |

## 10. 验证证据（文档/设计阶段）

| 验证项 | 命令/方式 | 结果 |
|---|---|---|
| 页面地图冒烟 | `python -X utf8 docs/product/ue/verify_map.py` | 18 页面 / 29 边；详情/跳转/模块/搜索/缩放/页面图/UE 标注图均通过；console errors 0 |
| 线框总览冒烟 | `python -X utf8 docs/product/ue/verify_wireframes.py` | 18 卡片 / 18 地图链接；console errors 0 |
| 文档内链 | `python scripts/check-links.py` | 41 个 Markdown 文件，全部相对链接可解析 |
| 本地目录 ignore | `git check-ignore -v Resource learning tools .obsidian .omo` | 均命中 `.gitignore` |
| 目录骨架 | `dir /s /b apps services packages` | 40 个 `.gitkeep` 占位；与 `06-file-tree.md` 一致 |
| 费用来源 | `19-cost-research.md` | 官方/政府采购/云厂商/转载来源已标注；价格有日期/地区 |
| 待代码验证 | 后端/小程序/数据库/DeepSeek | 尚未开始，不能标记 DONE |

## 11. 下一步

1. 继续 B-002：按 11.06–11.12 排期开始代码（FastAPI/SQLite/原生小程序/DeepSeek）。
2. 每完成一天更新本记录和 `04-tasks.md`。
3. 11.12 交付后写复盘，进入 B-003。
