# Spec Delta

## ADDED Requirements

### Requirement: Forced knowledge-base mode skips web search

当出题请求显式指定用户拥有的 `knowledge_base_id` 时，系统 MUST 仅在该知识库内检索取知并出题，MUST NOT 调用联网搜索或网页抽取；题目与讲解 MUST 以检索到的库内材料为准，少编造材料外事实。

#### Scenario: Start from bank with knowledge_base_id

- **WHEN** 已登录用户从题库选择自己的就绪知识库开局，并在出题请求中带上该 `knowledge_base_id`
- **THEN** 系统 MUST 仅检索该库内容生成题目，且 MUST NOT 调用联网搜索工具

#### Scenario: Forced mode with insufficient material fails clearly

- **WHEN** 指定知识库在强制模式下检索不到足以出题的内容（或库无就绪文档）
- **THEN** 系统 MUST 返回可读失败，MUST NOT 静默改用模型常识或联网搜索冒充「材料闯关」

### Requirement: Homepage agent may retrieve from user's knowledge bases

当首页文本开局（未指定 `knowledge_base_id`）且当前用户至少有一个含就绪文档的知识库时，取知 Agent MUST 能够调用知识库检索工具，并自行决定使用库内检索、联网搜索/抽取，或二者组合。

#### Scenario: Agent routes to private knowledge when topic matches

- **WHEN** 用户主题明显对应其私有资料领域，且用户存在就绪知识库
- **THEN** 取知 Agent MUST 能够选择调用知识库检索，并将检索片段纳入后续出题依据

#### Scenario: Agent may still use web tools when useful

- **WHEN** 用户有就绪知识库，但主题更适合公开网页知识
- **THEN** 取知 Agent MUST 仍可选择联网搜索或抽取，而不强制只用知识库

### Requirement: Material-first rules apply when knowledge-base context is used

只要本局出题实际使用了知识库检索片段（含强制库模式与首页 Agent 选用库检索），讲解与考点 MUST 优先依据这些片段；MUST NOT 把库外常识写成「资料已写明」的断言。

#### Scenario: Explanation cites library facts preferentially

- **WHEN** 出题上下文包含知识库检索片段
- **THEN** 正确答案与 explanation MUST 与片段一致或可从片段合理推出，不得捏造与片段冲突的「资料事实」

## MODIFIED Requirements

### Requirement: Every quiz generation attempts web grounding

对未指定 `knowledge_base_id` 的首页文本开局：若当前用户**没有任何含就绪文档的知识库**，系统 MUST 尝试联网取知增强（与历史行为一致）；若用户**有就绪知识库**，系统 MUST 运行可同时使用「知识库检索」与「联网搜索/抽取」的 Agent 路由取知，而不是无条件每次只走联网。两种情况均不得要求用户手动开启增强，也不得强制展示检索来源或要求确认来源后再开局。指定了 `knowledge_base_id` 的请求不适用本条的联网义务（见强制知识库模式）。

#### Scenario: Keyword topic triggers enhanced generation

- **WHEN** 已登录用户提交非空主题线索文本（非纯 URL）并请求出题，且未指定 `knowledge_base_id`
- **THEN** 系统在返回题目之前 MUST 完成取知增强（无就绪库时尝试联网搜索；有就绪库时由 Agent 在知识库检索与联网工具间路由），并据此生成结构化题目

#### Scenario: No ready knowledge base uses web grounding

- **WHEN** 已登录用户提交非空主题线索且未指定 `knowledge_base_id`，且该用户没有任何含就绪文档的知识库
- **THEN** 系统在返回题目之前 MUST 尝试通过联网搜索获取与该主题相关的外部内容，并据此生成结构化题目

#### Scenario: User with knowledge bases gets agentic routing

- **WHEN** 已登录用户提交非空主题线索且未指定 `knowledge_base_id`，且该用户至少有一个含就绪文档的知识库
- **THEN** 系统 MUST 通过 Agent 在知识库检索与联网工具之间自主选择取知路径后再出题，且不得要求用户先选模式

#### Scenario: User does not see sources

- **WHEN** 出题成功并进入闯关
- **THEN** 客户端响应与 UI MUST NOT 强制展示检索来源或要求用户确认材料；用户直接进入答题流程

### Requirement: Agent chooses search vs extract tools

在适用联网工具的出题流程中，系统 MUST 将「关键词搜索」与「按 URL 抽取全文」作为可调用能力交给模型侧决策；当用户存在就绪知识库且未强制指定库时，还 MUST 将「知识库检索」一并交给模型决策。模型自行决定何时调用哪个工具、调用几次。系统 MUST NOT 依赖在单次搜索调用中动态改写结果条数、是否返回全文、国家偏向等仅允许在工具构造时设定的参数；深度网页内容通过抽取工具获得；知识库深度内容通过库内检索获得。

#### Scenario: Simple topic uses search summaries

- **WHEN** 主题为常见、相对简单的知识线索且 Agent 选择联网路径
- **THEN** 出题流程 MAY 仅使用关键词搜索返回的摘要级结果完成取知，再生成题目

#### Scenario: Complex or novel topic uses extract for full content

- **WHEN** 主题为较新、较复杂或易被模型混淆的知识线索且 Agent 选择联网路径
- **THEN** 出题流程 MUST 能够通过对相关 URL 调用页面抽取获取更完整正文，再据此出题，避免仅凭训练记忆硬编

#### Scenario: Domestic vs international focus

- **WHEN** 主题明显偏向中国或海外语境且 Agent 选择联网路径
- **THEN** 出题流程 MUST 能够选用对应的预置搜索能力（例如默认全球搜索，或偏中国结果的搜索预置），优先获取更相关地域的结果；不要求城市级检索

#### Scenario: Knowledge retrieve tool available when user has ready libraries

- **WHEN** 用户有就绪知识库且请求未指定 `knowledge_base_id`
- **THEN** 取知 Agent 的工具集 MUST 包含可按查询检索用户知识库内容的能力

### Requirement: Silent fallback to model-only generation

当**未指定** `knowledge_base_id` 的首页开局中，联网检索、页面抽取与（若启用）知识库检索均失败、超时、无可用结果，或增强链路整体失败时，系统 MUST 静默回退为仅使用模型已有知识围绕主题出题；MUST NOT 因此向用户展示「检索失败」「已降级」等专用提示。强制知识库模式不适用本条静默降级（见强制模式失败场景）。

#### Scenario: Tavily unavailable

- **WHEN** 外部检索服务不可用或密钥缺失导致联网取知失败，且未指定 `knowledge_base_id`
- **THEN** 系统仍 MUST 尝试用模型知识生成合法题目并成功返回（若模型出题本身也失败，则沿用既有出题失败错误响应）；若此时知识库检索仍可用，Agent MAY 先使用库内结果而不必降级

#### Scenario: Empty search results

- **WHEN** 联网搜索与抽取均未得到可用于出题的内容，且知识库检索也无可用结果或未启用，且未指定 `knowledge_base_id`
- **THEN** 系统 MUST 静默降级为模型知识出题，且成功响应的字段形状与增强成功时一致

### Requirement: Quiz API contract remains compatible

`POST /api/v1/quiz/generate`（及等价的异步出题创建接口）的既有请求字段 `source_text`、可选 `topic_name`、`question_count` 与成功响应 `topic_name` + 结构化 `questions` MUST 保持兼容。系统 MAY 增加**可选**字段 `knowledge_base_id`；未传该字段时行为遵循首页 Agent 路由规则，不得因缺少该字段而失败。

#### Scenario: Existing client continues to work

- **WHEN** 现有小程序客户端按原请求体（无 `knowledge_base_id`）调用出题接口
- **THEN** 系统 MUST 返回可被现有前端解析的 `QuizPayload`，无需为知识库能力新增必填请求字段

#### Scenario: Optional knowledge_base_id selects forced mode

- **WHEN** 客户端传入属于当前用户的有效 `knowledge_base_id`
- **THEN** 系统 MUST 按强制知识库模式出题，成功响应字段形状仍与既有 `QuizPayload` 兼容
