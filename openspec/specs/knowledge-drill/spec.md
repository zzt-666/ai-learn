# knowledge-drill Specification

## Purpose

为私有知识库提供库级「刷题 / 学透」模式，并在刷题模式下将正式题库文档拆成可抽题的结构化题目，支持已刷记录、复习轮与解析补全，解决纯 RAG Top-K 无法覆盖整本题库的问题。

## Requirements

### Requirement: Knowledge base has a single locked mode

系统 MUST 以知识库为单位设置模式，取值仅为刷题（drill）或学透（master）；同一知识库 MUST NOT 同时按两种模式运行。模式经用户确认后锁定；后续新文档 MUST 按该库模式处理或在不符时提醒用户。

#### Scenario: Confirm drill mode for a knowledge base

- **WHEN** 用户确认某知识库为刷题模式
- **THEN** 系统 MUST 将该库标记为刷题，且后续从该库开局 MUST 走刷题抽题路径而非学透 RAG 生成路径

#### Scenario: Confirm master mode for a knowledge base

- **WHEN** 用户确认某知识库为学透模式
- **THEN** 系统 MUST 将该库标记为学透，且后续从该库开局 MUST 走材料优先检索生成路径

### Requirement: System suggests mode and user confirms

上传或入库分析后，系统 MUST 可给出刷题或学透的建议并预选；模式 MUST 在用户确认（或明确改选）后生效。系统 MUST NOT 在未告知用户的情况下静默改写已锁定的库模式。

#### Scenario: Suggestion preselects but waits for confirm

- **WHEN** 后台根据文档特征建议刷题模式
- **THEN** 客户端 MUST 展示建议原因并允许用户确认或改选学透后再生效

### Requirement: Drill ingest extracts structured text questions

在刷题模式知识库中，系统 MUST 从支持的文档中拆出结构化题目并持久化；本期 MUST 仅入库单选、多选、判断的文本题。图片题 MUST 被过滤且 MUST NOT 进入可抽题集合。拆题 MUST 优先规则解析，在规则失败或置信度不足时 MAY 使用模型辅助补拆。

#### Scenario: Formal question bank PDF yields multiple choice items

- **WHEN** 用户向刷题库上传版式规范的题库 pdf/docx/md 且拆题成功
- **THEN** 系统 MUST 产生一条或多条含题干、选项与答案的结构化题目记录，状态可用于开局抽题

#### Scenario: Image-only items are filtered

- **WHEN** 拆题过程识别到依赖图片才能作答的题目
- **THEN** 系统 MUST NOT 将其纳入可刷题集合，并 MAY 在文档状态或提示中反映已过滤

#### Scenario: Non-fitting document is warned

- **WHEN** 用户向刷题库上传明显不像题库的学习资料，或拆题后可用文本题过少/为零
- **THEN** 系统 MUST 提醒用户文档可能不符当前库模式，MUST NOT 静默把该库改成学透

### Requirement: Drill session samples by question count with practice memory

刷题开局时，系统 MUST 允许用户选择本局题量 N，并从该库可刷题集合中抽取至多 N 道题；抽取 MUST 优先未刷题目。已刷记录 MUST 持久化在服务端并按用户与知识库隔离。本局组装题目 MUST NOT 依赖把整库原文塞进模型上下文，也 MUST NOT 仅靠向量 Top-K 再生成整卷作为覆盖手段。

#### Scenario: Prefer unseen questions

- **WHEN** 用户在刷题库选择 N=6 且库内未刷题不少于 6 道
- **THEN** 系统 MUST 返回 6 道此前未刷（或标记为未完成轮转）的题目进入闯关

#### Scenario: Fewer than N available

- **WHEN** 用户选择的 N 大于当前可抽题数量
- **THEN** 系统 MUST 按实际可抽数量出题并提示数量不足，MUST NOT 伪造题目凑满 N

### Requirement: Completed rotation offers review or reset

当刷题库中用户的未刷池为空时，系统 MUST 在开局前明确提示本库已全部刷过一遍，并提供复习轮、重置刷题进度（需确认）或取消；MUST NOT 在无提示情况下将已刷题伪装为新题继续抽取。

#### Scenario: Start review round after full coverage

- **WHEN** 未刷池为空且用户选择开始复习轮并指定题量 N
- **THEN** 系统 MUST 从已刷题目中再抽取至多 N 道供本局作答，并告知这是复习轮

#### Scenario: Reset practice progress

- **WHEN** 用户确认重置该库刷题进度
- **THEN** 系统 MUST 清空该用户在该库的已刷记录，使题目重新进入未刷池

### Requirement: Missing explanation can be AI-filled lazily

刷题题目若原文带有解析，系统 MUST 优先展示原文解析。若无解析，系统 MUST 允许在用户提交该题后按需生成 AI 解析并缓存到该题，避免每次重复生成；展示 MUST 能区分原文解析与 AI 生成解析。

#### Scenario: Lazy generate explanation after answer

- **WHEN** 用户提交一道无原文解析的刷题题目
- **THEN** 系统 MAY 生成并缓存讲解，后续再次查看同一题 MUST 复用缓存且标明为 AI 生成

### Requirement: Mismatch blocks bad drill starts

当刷题库无可用题目，或用户试图在不符/失败状态下开刷时，系统 MUST 阻断刷题开局并给出可读说明，同时提供改学透或更换/删除文档等明确操作入口。

#### Scenario: Zero usable questions cannot start drill

- **WHEN** 刷题库可用文本题数量为 0 且用户点击开始闯关
- **THEN** 系统 MUST 拒绝开局并提示原因，不得进入空卷或乱题闯关
