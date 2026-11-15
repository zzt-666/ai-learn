# Design

## Context

- 现状：`backend/app/services/quiz_service.py` 用 `ChatDeepSeek` + `with_structured_output(QuizPayload)`，Prompt 明确「主题线索 + 模型知识」，无外部检索。
- 约束：只改出题链路；`POST /api/v1/quiz/generate` 契约不变；登录/历史/报告/结算不动；不做 RAG。
- 用户确认：每次出题都增强；兼容关键词搜索与 URL 抽全文；使用 LangChain 官方 `TavilySearch` / `TavilyExtract`；模型自行决定调用哪个工具；失败静默降级；不展示来源。
- 策略修订：采用「官方工具 + 固定合理默认 + 可选偏中国 Search 预置」，**不做**按次动态包装传 `max_results` / `include_raw_content` / `country`。
- 文档依据（实现前须再核对最新版）：
  - https://docs.langchain.com/oss/python/integrations/tools/tavily_search
  - https://docs.langchain.com/oss/python/integrations/tools/tavily_extract
  - Context7：`/tavily-ai/langchain-tavily`、`/websites/langchain_oss_python_langchain`（`create_agent` + `response_format`）

## Goals / Non-Goals

**Goals:**

- 在服务端出题路径中接入 Tavily 搜索 + 抽取，由 Agent 决定调用哪个工具。
- 简单主题靠搜索摘要；复杂/新知识或用户贴 URL 靠 Extract 全文。
- 有检索上下文时优先依据外部内容出题；无有效上下文时走现有结构化出题链。
- 保持 `QuizPayload` 校验、题型配比与既有重试策略。

**Non-Goals:**

- 自研「按次实例化」动态参数包装层，在每次 invoke 伪装动态改 `max_results` / `include_raw_content` / `country`。
- 前端来源预览/确认、RAG 入库、持久化检索快照、报告链改造。
- 替换 DeepSeek 或改题型 Schema。
- 城市级地理检索（Tavily 仅有 `country`，无 city）。

## Decisions

### 1. 出题编排：Agent 取知 + 结构化出题（可同图或两段）

**选择：** 使用 LangChain `create_agent`，绑定官方搜索/抽取工具；最终产出仍是校验后的 `QuizPayload`。

优先路径：

1. Agent 携带 `TavilySearch` / `TavilyExtract`（及可选偏中国 Search），根据 `source_text` 自行检索/抽页。
2. 用收集到的外部文本 + 原主题线索，调用（或同一 Agent 的）结构化输出得到 `QuizPayload`。
3. 跑现有 `validate_quiz_mix`；失败有限重试。

**备选（若 DeepSeek 无法稳定同时 tool-call + structured output）：** 明确拆成两段——Research Agent（只取知，返回拼接后的 `research_context` 字符串）→ 现有 `with_structured_output` 出题链（Prompt 注入 `research_context`）。两段在产品行为上等价，实现阶段以联调结果二选一，默认先试单 Agent + `response_format`（见 LangChain structured output / `ToolStrategy`）。

**不选：** 规则引擎写死「有 URL 就 extract、否则 search」——与「把工具交给 AI 决定」冲突。

### 2. 工具装配：官方实例 + 固定默认 + 可选中国预置

**问题：** 现行 `langchain-tavily` 规定 `max_results`、`include_raw_content`、`country`、`include_answer` 等**只能在实例化时设置**，invoke 传入会 `ValueError`。全动态包装虽可行，但增加维护成本，对本期收益有限。

**选择（推荐）：**

1. **默认全球 Search**（名称对模型可为 `tavily_search`）  
   构造示例意图：`max_results=5`，`include_raw_content=False`，`topic="general"`，不设 `country`。  
   Agent 在 invoke 时仍可使用官方允许字段（如 `query`、`search_depth`、`include_domains`、`time_range` 等）。

2. **Extract**（`tavily_extract`）  
   官方 `TavilyExtract`；用于用户粘贴的 URL，或搜索命中后需要全文时再抽。`extract_depth` 按官方允许方式设置（构造默认 `basic`，invoke 可调若文档允许）。

3. **可选偏中国 Search**（名称如 `tavily_search_china`）  
   与默认 Search 相同默认条数/摘要策略，但构造时设 `country="china"`（仅 `topic=general` 有效）。Agent 在国内语境主题时选用该工具。

**深度策略（替代动态 `include_raw_content`）：**

- 简单主题 → 主要 `tavily_search` 摘要即可。  
- 复杂/新术语 → 先 search 找可靠 URL，再 `tavily_extract` 取正文。  
- 用户输入已含 URL → 优先/并行 extract。

**不选：**

- 按次构造包装层暴露全动态 `max_results` / `include_raw_content` / `country`。  
- 注册十几个冻结参数的搜索变体（组合爆炸）。

### 3. Prompt / 知识优先级

增强成功时 System/Human Prompt 调整为：

1. 优先依据「联网检索/抽取得到的内容」出题与写讲解；
2. 用户 `source_text` 仍是主题/线索（可含 URL）；
3. 禁止字面弱题；题型规则不变；
4. 若外部内容与常识冲突，以外部权威内容为准（针对新术语场景，避免再落到错误领域）；
5. 引导：简单主题少调用、优先摘要搜索；复杂主题对关键 URL 使用 extract；国内语境可选用偏中国搜索工具。

降级路径复用现有 `QUIZ_SYSTEM` / `QUIZ_HUMAN`（或等价「无 research_context」分支）。

### 4. 静默降级策略

下列情况 **不** 向客户端增加错误码或文案，直接走模型知识出题：

- 缺少 `TAVILY_API_KEY`
- Tavily HTTP/超时/额度错误
- 工具返回空 `results` 且无可用正文
- Research Agent 异常（捕获后降级）

仅当**最终结构化出题**仍失败时，返回既有 `GENERATE_FAILED`。

日志可记 `quiz_grounding=degraded|ok`（禁止打印全文 `source_text` / 长 raw_content）。

### 5. 依赖与配置

```text
langchain-tavily   # TavilySearch, TavilyExtract
langgraph          # create_agent 运行时（按当前 LangChain 文档）
```

`.env` / `.env.example` 增加：

```text
TAVILY_API_KEY=
# 可选：出题 Agent 总超时（含多轮工具），默认高于现 QUIZ_TIMEOUT
QUIZ_AGENT_TIMEOUT_SECONDS=120
```

`Settings` 读取上述项；密钥仅服务端。

### 6. 前端与超时

- API 不变 → 前端类型与请求可不动。
- 出题可能变慢：后端超时调高；前端 loading 可改为「正在检索并出题…」（可选，非契约变更）。
- 不新增来源展示 UI。

### 7. 测试策略

- **单元/装配：** 断言绑定的是官方 `TavilySearch` / `TavilyExtract` 实例及预期构造默认（含可选 china 预置的 `country`）；mock 工具返回。
- **服务：** mock Tavily + mock LLM：有检索上下文时走增强；Tavily 抛错时静默降级且仍返回合法 `QuizPayload`；覆盖「仅 search」「search + extract」「纯 URL extract」路径。
- **契约：** 现有 `test_quiz_api` 在 mock `generate_quiz` 下保持绿；增加增强/降级分支测试。
- 不依赖真实 Tavily/DeepSeek 做 CI 主路径。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| DeepSeek 对多轮 tool call + 结构化输出不稳定 | 两段式 Research → Structured Quiz；实现阶段用 Context7/官方文档核对 `create_agent` + DeepSeek |
| 出题耗时/费用上升 | 限制 Agent 最大工具轮次；Prompt 引导简单主题少调用；超时后降级 |
| 固定 `max_results` 对极难主题不够 | 靠多轮 search + extract 补深度，而非动态改条数 |
| 错误网页内容误导出题 | Prompt 要求多源交叉与概念题；后续可加域名白名单（本期不做） |
| `country` 无法表达「城市」 | 仅提供全球 / 偏中国两个预置；接受 API 能力边界 |

## Migration Plan

1. 加依赖与 `TAVILY_API_KEY`（本地人工填）。
2. 装配官方工具 + 增强 `generate_quiz`；保留降级分支。
3. 单测通过后联调：关键词新主题（如 Harness Engineering）、纯 URL、国内语境（偏中国工具）、检索失败降级。
4. 可选微调前端 loading 文案。
5. 回滚：配置关闭增强或代码回退至仅 `with_structured_output` 路径（建议保留 `QUIZ_WEB_GROUNDING=true` 开关便于紧急关闭，默认 `true`）。

## Open Questions

- DeepSeek 与 `create_agent` + `response_format` 同开是否一次联调即稳定 → 实现时验证；不稳定则固定两段式，不改规格行为。
- `QUIZ_WEB_GROUNDING` 紧急开关默认开；若产品坚持「代码层无开关、仅靠降级」，实现时可去掉开关，不影响规格。
