# Spec Delta

## ADDED Requirements

### Requirement: Forced knowledge base start respects library mode

当出题请求指定用户拥有的 `knowledge_base_id` 时，系统 MUST 读取该库已确认的模式并分流：刷题（drill）库 MUST 从已拆题目中按题量组装本局题目进入闯关；学透（master）库 MUST 继续以库内检索材料优先生成题目。刷题分流 MUST NOT 调用联网搜索，也 MUST NOT 以「仅 Top-K 检索再生成整卷」作为覆盖整本题库的手段。

#### Scenario: Drill library assembles sampled questions

- **WHEN** 已登录用户从刷题模式知识库开局并请求题量 N，且库内有足够可用文本题
- **THEN** 系统 MUST 返回结构化 `questions`（题型限于单选/多选/判断），题目来源于该库已拆题记录，成功响应字段形状与既有闯关载荷兼容

#### Scenario: Master library keeps material-first generation

- **WHEN** 已登录用户从学透模式知识库开局并带上该 `knowledge_base_id`
- **THEN** 系统 MUST 在该库内检索取知并生成题目（材料优先），MUST NOT 走刷题抽题表作为唯一来源

#### Scenario: Drill start blocked when bank not ready

- **WHEN** 用户对刷题库开局但可用题目为 0 或拆题未完成导致不可抽
- **THEN** 系统 MUST 失败并返回可读错误，MUST NOT 静默改用联网或模型编造整卷冒充刷题
