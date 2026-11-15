# Tasks

## 1. Dependencies and configuration

- [x] 1.1 用 Context7 / 官方文档确认当前 `langchain-tavily`、`create_agent`、DeepSeek tool-calling 的推荐安装与用法后，将 `langchain-tavily`、`langgraph`（及文档要求的配套包）写入 `backend/requirements.txt`，并在本地安装成功（`pip install -r requirements.txt` 无报错）
- [x] 1.2 在 `backend/.env.example` 与 `Settings` 增加 `TAVILY_API_KEY`、`QUIZ_AGENT_TIMEOUT_SECONDS`（可选 `QUIZ_WEB_GROUNDING` 默认 true）；验证 `get_settings()` 能读到新字段

## 2. Official Tavily tool assembly

- [x] 2.1 装配默认全球 `TavilySearch`（固定合理默认：如 `max_results=5`、`include_raw_content=False`、`topic="general"`、不设 country）与官方 `TavilyExtract`；用单测或装配断言确认实例类型与关键构造默认，且无自研「按次动态包装」层
- [x] 2.2 装配可选偏中国 `TavilySearch` 预置（如 `country="china"`，其余默认与全球搜一致，工具名对模型可区分）；单测断言 `country` 仅在该预置构造时生效
- [x] 2.3 为工具调用路径补充 mock：「API 抛错 / 空结果」时上层可识别并降级；验证相关单测通过

## 3. Grounded quiz generation service

- [x] 3.1 新增/更新出题 Prompt：有 `research_context` 时优先依据联网内容；引导简单主题用搜索摘要、复杂/URL 用 extract、国内语境可选用偏中国搜索；禁止字面弱题；题型规则不变；用快照或字符串断言关键约束仍在 Prompt 中
- [x] 3.2 实现 Research/出题 Agent 编排（优先 `create_agent` + 官方工具列表；若 DeepSeek 不稳定则改为「Agent 取知 → 现有 `with_structured_output`」两段式）：输入 `source_text` / `topic_name` / `question_count`，输出可校验的 `QuizPayload`；单元测试用 mock 工具与 mock LLM 覆盖「仅 search」「search + extract」「纯 URL extract」路径
- [x] 3.3 在 `generate_quiz` 中接入增强路径：默认每次尝试联网；`validate_quiz_mix` 与有限重试保留；缺少 key / 工具失败 / 空结果时静默调用原模型出题链；测试断言降级时**不**改错误码文案且仍返回合法 payload
- [x] 3.4 确认 `POST /api/v1/quiz/generate` 请求/响应模型未改；现有 `test_quiz_api` 在 mock 下仍通过，并新增至少一条「增强成功」与一条「静默降级」的 router/service 级测试

## 4. Frontend polish (optional) and integration check

- [x] 4.1 （可选）将出题 loading 文案改为体现「检索并出题」且不展示来源；若跳过则在 PR/说明中注明「前端未改」
- [x] 4.2 本地联调清单跑通并记录结果：① 新术语关键词（如 Harness Engineering）② 纯 URL 输入 ③ 国内语境主题（偏中国工具）④ 故意无效 `TAVILY_API_KEY` 或 mock 失败后的静默降级；确认历史/登录/报告路径未被改动

## Workflow follow-up

- Archive the change after implementation review (`openspec-archive-change` or equivalent).
- 实现阶段须再次用 Context7 / 官方文档核对 Taro（若改前端）与 LangChain/Tavily API，避免过时用法。
