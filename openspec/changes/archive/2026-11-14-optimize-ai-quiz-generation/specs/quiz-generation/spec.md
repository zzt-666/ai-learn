# Spec Delta

## Purpose

定义首页文本开局时 AI 生成闯关题目的行为：默认联网检索增强、兼容关键词与网址输入、检索失败静默降级，并继续输出可校验的结构化题目。

## ADDED Requirements

### Requirement: Every quiz generation attempts web grounding

系统 MUST 在每一次首页闯关出题请求中尝试联网取知增强，且不得要求用户手动开启增强，也不得向用户展示检索来源列表或要求确认来源后再开局。

#### Scenario: Keyword topic triggers enhanced generation

- **WHEN** 已登录用户提交非空主题线索文本（非纯 URL）并请求出题
- **THEN** 系统在返回题目之前 MUST 尝试通过联网搜索获取与该主题相关的外部内容，并据此生成结构化题目

#### Scenario: User does not see sources

- **WHEN** 出题成功并进入闯关
- **THEN** 客户端响应与 UI MUST NOT 强制展示检索来源或要求用户确认材料；用户直接进入答题流程

### Requirement: URL input can be extracted as full page content

当用户输入包含可识别的网页 URL 时，系统 MUST 能够获取该页面正文内容，并用于后续出题；同一请求中也可结合关键词搜索补充相关知识。

#### Scenario: Paste a URL as source_text

- **WHEN** 用户提交的 `source_text` 主要为或包含一个 http(s) 网址
- **THEN** 系统 MUST 尝试抽取该 URL 的页面正文，并将抽取结果纳入出题依据

#### Scenario: Mixed clue with URL and keywords

- **WHEN** 用户输入同时包含主题关键词与网址
- **THEN** 系统 MUST 允许同时使用页面抽取与关键词搜索（由出题流程自行选择调用顺序与次数），最终仍返回合法题目列表

### Requirement: Agent chooses search vs extract tools

出题流程 MUST 将「关键词搜索」与「按 URL 抽取全文」作为可调用能力交给模型侧决策：模型自行决定何时调用哪个工具、调用几次。系统 MUST NOT 依赖在单次搜索调用中动态改写结果条数、是否返回全文、国家偏向等仅允许在工具构造时设定的参数；深度内容通过调用抽取工具获得。

#### Scenario: Simple topic uses search summaries

- **WHEN** 主题为常见、相对简单的知识线索
- **THEN** 出题流程 MAY 仅使用关键词搜索返回的摘要级结果完成取知，再生成题目

#### Scenario: Complex or novel topic uses extract for full content

- **WHEN** 主题为较新、较复杂或易被模型混淆的知识线索
- **THEN** 出题流程 MUST 能够通过对相关 URL 调用页面抽取获取更完整正文，再据此出题，避免仅凭训练记忆硬编

#### Scenario: Domestic vs international focus

- **WHEN** 主题明显偏向中国或海外语境
- **THEN** 出题流程 MUST 能够选用对应的预置搜索能力（例如默认全球搜索，或偏中国结果的搜索预置），优先获取更相关地域的结果；不要求城市级检索

### Requirement: Silent fallback to model-only generation

当联网检索或页面抽取失败、超时、无可用结果，或增强链路整体失败时，系统 MUST 静默回退为仅使用模型已有知识围绕主题出题；MUST NOT 因此向用户展示「检索失败」「已降级」等专用提示。

#### Scenario: Tavily unavailable

- **WHEN** 外部检索服务不可用或密钥缺失导致取知失败
- **THEN** 系统仍 MUST 尝试用模型知识生成合法题目并成功返回（若模型出题本身也失败，则沿用既有出题失败错误响应）

#### Scenario: Empty search results

- **WHEN** 联网搜索与抽取均未得到可用于出题的内容
- **THEN** 系统 MUST 静默降级为模型知识出题，且成功响应的字段形状与增强成功时一致

### Requirement: Quiz API contract remains compatible

`POST /api/v1/quiz/generate` 的请求与成功响应字段 MUST 保持与现有契约兼容：请求仍为 `source_text`、可选 `topic_name`、`question_count`；成功响应仍为 `topic_name` 与结构化 `questions`（含题型、选项、答案下标、讲解）。

#### Scenario: Existing client continues to work

- **WHEN** 现有小程序客户端按原请求体调用出题接口
- **THEN** 系统 MUST 返回可被现有前端解析的 `QuizPayload`，无需为增强出题新增必填请求字段

### Requirement: Structured quiz quality rules still apply

无论是否成功取到联网内容，生成的题目 MUST 继续满足既有业务规则：简体中文；混合单选/多选/判断；题量等于请求 N；禁止字面检索弱题；每题含正确答案与讲解；服务端校验失败可重试后再失败。

#### Scenario: Grounded questions are still non-literal

- **WHEN** 出题依据包含检索或抽取正文
- **THEN** 题目 MUST 考察概念理解或辨析，MUST NOT 退化为「材料里出现了哪些字」类弱题

#### Scenario: Validation failure retry

- **WHEN** 模型返回的题目未通过题型配比或字段校验
- **THEN** 系统 MUST 按既有策略重试有限次数；仍失败则返回既有出题失败错误，不得返回半合法题目列表
