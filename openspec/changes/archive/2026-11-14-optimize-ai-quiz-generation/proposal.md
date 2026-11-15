# Proposal

## Why

大模型训练数据有截止时限；用户学习很新的主题（例如 Harness Engineering）时，当前「仅主题线索 + 模型知识」出题会张冠李戴、编造错误考点。需要在每次首页闯关出题前接入联网检索与网页抽取，用实时权威内容校准出题，同时兼容「关键词」与「粘贴网址」两种输入。

## What Changes

- 每次调用 `POST /api/v1/quiz/generate` 均走联网增强出题（默认全开，无用户开关、无来源展示）。
- 出题 Agent 直接绑定官方 **`TavilySearch`** 与 **`TavilyExtract`**（外加可选一个偏中国的 Search 预置），自行决定何时调用哪个工具；简单主题用搜索摘要，复杂/新知识或用户贴 URL 时用 Extract 取全文。
- Search 在构造时使用固定合理默认（如条数、不默认带全文）；不实现「按次动态包装传 `max_results` / `include_raw_content` / `country`」。
- 检索失败或无可用结果时：**静默降级**为现有「模型训练知识」出题，**不对用户提示**。
- 对外 API 契约（请求/响应字段）保持不变；前端无需展示来源，仅可微调 loading 文案（可选）。
- 新增服务端依赖：`langchain-tavily`（及 Agent 运行所需的 `langgraph` 等），环境变量增加 `TAVILY_API_KEY`。
- **不做**：全动态参数包装层、RAG 知识库、来源确认 UI、历史/登录/报告结算改造、用户侧「材料为准」模式。

## Capabilities

### New Capabilities

- `quiz-generation`: 首页文本开局的 AI 出题行为，含联网检索增强、工具选型、静默降级与结构化题目输出。

### Modified Capabilities

- （无：仓库尚无既有 `openspec/specs` 能力规格）

## Impact

- **后端**：`quiz_service` / prompts / LLM 装配；装配官方 Tavily 工具与出题 Agent；`config` / `.env.example` / `requirements.txt`。
- **API**：路径与 `QuizPayload` 不变；出题耗时可能变长（超时与 loading 需对齐）。
- **前端**：主路径不变；可选更新出题等待文案；不展示检索来源。
- **不动**：登录、历史、重闯、通关结算、报告链。
- **外部**：Tavily API 额度与密钥；DeepSeek 需支持 tool calling。
