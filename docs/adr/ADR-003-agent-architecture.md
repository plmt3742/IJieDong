# ADR-003: Agent 架构

- 状态：Proposed（Step 4 实现中；AnswerBlocks 以 24 为准，ADR 工具名待同步）
- 日期：2026-11-06
- 决策人：项目开发者
- 相关任务：AI-001~008
- 相关文档：`docs/agent/05-architecture.md` §7/§8、`docs/agent/09-risks.md` R-007/R-008

## 1. 背景

需求方希望“通过问答快速调出数据/生成可视化图表”。政府数据场景有三个硬约束：

1. **数字必须准**：不能让模型编造/补 0/算错排名。
2. **权限与安全**：不能让模型直连数据库、生成任意 SQL/JS、越权查数据。
3. **可解释**：答案要能追溯到指标/区域/年份；图表要能复现。

同时是单人开发，不能引入过重的 Agent 框架/运维。

## 2. 决策

采用**受控工具调用 Agent**：

```text
用户问题
  → LLM（OpenAI 兼容）
  → 白名单只读工具（6–7 个）
  → 数据服务（参数校验/权限/行数上限）
  → LLM 生成最终 JSON（answer + citations + chart intent）
  → Pydantic + ChartSpec 校验
  → 返回 / 落库 / 审计
```

关键决策：

1. **不生成 SQL**：LLM 只能调用 `list_regions`、`list_indicators`、`get_indicator_values`、`rank_regions`、`compare_regions`、`get_region_profile`、`build_chart`。
2. **不生成 ECharts option/JS**：LLM 只产出 `ChartSpec`（类型/类别/系列/单位/排序），前端用固定渲染器。
3. **不用 LangChain/LlamaIndex**：直接用 OpenAI 兼容 SDK + 自写循环 + Pydantic；逻辑透明、易调试。
4. **Provider 抽象**：`LLM_BASE_URL`/`LLM_API_KEY`/`LLM_MODEL` 配置化；开发 DeepSeek，生产可切 Qwen/GLM/vLLM/Ollama。
5. **输出强校验**：最终 JSON 必须过 Pydantic；ChartSpec 必须过 schema；失败重试 1 次，仍失败返回可读错误。
6. **引用强制**：每个结论必须有 `citations`（指标/区域/年份/来源）；无数据明确拒答。
7. **限制**：最多 5 次工具调用、最多 500 行、30s 超时、答案 ≤2000 字；工具只读。
8. **评测**：50 题评测集；数字正确率 ≥95%，ChartSpec 合法率 ≥98%。

## 3. 后果

### 正面

- 数字由后端计算/查询，模型只负责理解和表达；准确性可控。
- 无 SQL/代码执行面，安全风险显著降低。
- 工具/输出可单测；评测可量化；问题可复现。
- 图表跨端一致（ChartSpec）；小程序/H5/后台共用渲染器。
- 供应商可切换；私有化可行。

### 负面/代价

- 灵活性受限：新类型问题需要加工具/改 Prompt。
- 复杂分析（多指标交叉、归因）需要更多工具/编排。
- Prompt/工具设计需要迭代；评测集要维护。
- 非流式响应延迟较高（目标 <10s）；小程序体验需 loading/分步提示。

### 风险与缓解

| 风险 | 缓解 |
|---|---|
| 模型选错工具/参数 | 工具描述清晰；Pydantic 校验；错误回传让模型重试 |
| 模型编造数字 | 工具返回结构化数据；答案必须引用；评测；无数据拒答 |
| 模型输出非 JSON | JSON 模式/重试/修复 Prompt；失败兜底 |
| 图表类型不合理 | ChartSpec 白名单 + 规则（文本不画图、饼图类别上限） |
| 延迟/成本 | 限制上下文/工具次数/答案长度；缓存；小模型 |
| 数据权限 | 工具按用户可见范围过滤；不返回越权区域 |

## 4. 备选方案

| 方案 | 优点 | 缺点 | 为什么没选 |
|---|---|---|---|
| Text-to-SQL | 灵活；什么问题都能查 | 注入/越权/幻觉/方言/性能风险；难审计 | 政府数据不可接受 |
| RAG（文档向量检索） | 适合非结构化文档 | 不适合精确数值/排名；引用弱 | 当前数据是结构化指标 |
| LangChain/LlamaIndex Agent | 现成工具/记忆 | 抽象重、调试难、依赖多 | 单人维护成本高 |
| 微调模型 | 领域语气/格式 | 需要数据/算力；不能解决取数 | 本期不需要 |
| 让 LLM 直接出 ECharts option | 灵活 | 非法配置/安全/跨端不一致 | 不可控 |
| 固定报表 + 模板问答 | 最稳 | 不满足“自然语言”需求 | 作为降级/兜底可以 |

## 5. 实施要点

1. `app/ai/client.py`：OpenAI 兼容客户端；超时/重试/日志。
2. `app/ai/tools.py`：工具 schema + 执行器；只读；参数校验；行数上限。
3. `app/ai/agent.py`：循环（最多 5 次）、消息裁剪、最终 JSON 解析。
4. `app/ai/prompts.py`：system prompt + few-shot + 修复 prompt。
5. `app/ai/chart.py`：ChartSpec 构建/校验；类型规则。
6. `app/ai/validator.py`：Pydantic/JSON Schema；引用完整性检查。
7. `tests/fixtures/ai_eval/`：50 题；mock LLM 的单元测试 + 真实模型的评测脚本（手动跑）。
8. 日志：模型/耗时/token/工具调用/校验结果；不记录密钥。
9. 缓存（P1）：问题归一化 + 数据版本；命中缓存要标注。

## 6. 复审条件

- 评测中 >20% 问题无法用现有工具回答 → 增加工具/调整范围。
- 数字正确率 <95% 或 ChartSpec 合法率 <98% → 暂停上线，改 Prompt/工具/校验。
- 延迟 >15s 或成本超预算 → 换小模型/缓存/减少上下文。
- 需求要求复杂归因/预测 → 评估分析型工具/独立服务。
- 必须私有化且 OpenAI 兼容层不满足 → 评估专用推理服务。

## 7. 链接

- `docs/agent/05-architecture.md` §7/§8
- `docs/agent/09-risks.md` R-007/R-008/R-013
- `docs/agent/12-open-questions.md` Q-04/Q-13
