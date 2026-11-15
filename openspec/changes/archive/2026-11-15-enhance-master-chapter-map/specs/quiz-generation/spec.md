# Spec Delta

## MODIFIED Requirements

### Requirement: Forced knowledge base start respects library mode

当出题请求指定用户拥有的 `knowledge_base_id` 时，系统 MUST 读取该库已确认的模式并分流：刷题（drill）库 MUST 从已拆题目中按题量组装本局题目进入闯关；学透（master）库在要点地图 ready 时 MUST 按未覆盖优先的要点集合取知并生成题目，本局上下文 MUST 以选中要点摘要为主、可选附带少量库内原文片段，MUST NOT 把全文塞进一次 Prompt，也 MUST NOT 仅靠「固定库线索 + 整库 Top‑K」作为覆盖整份材料的手段。地图 pending/failed 或无可用要点时，系统 MUST 明确降级或阻断（含可读错误码/文案），不得静默假装已按覆盖学透开局。刷题分流 MUST NOT 调用联网搜索，也 MUST NOT 以「仅 Top-K 检索再生成整卷」作为覆盖整本题库的手段。

#### Scenario: Drill library assembles sampled questions

- **WHEN** 已登录用户从刷题模式知识库开局并请求题量 N，且库内有足够可用文本题
- **THEN** 系统 MUST 返回结构化 `questions`（题型限于单选/多选/判断），题目来源于该库已拆题记录，成功响应字段形状与既有闯关载荷兼容

#### Scenario: Master library keeps material-first generation

- **WHEN** 已登录用户从学透模式知识库开局并带上该 `knowledge_base_id`，且要点地图为 ready 且存在可取样要点
- **THEN** 系统 MUST 按题量估算并选取要点（未覆盖优先），据此在材料优先约束下生成题目，MUST NOT 走刷题抽题表作为唯一来源，MUST NOT 联网搜索

#### Scenario: Drill start blocked when bank not ready

- **WHEN** 用户对刷题库开局但可用题目为 0 或拆题未完成导致不可抽
- **THEN** 系统 MUST 失败并返回可读错误，MUST NOT 静默改用联网或模型编造整卷冒充刷题

#### Scenario: Master falls back when map not ready

- **WHEN** 用户从学透库开局但地图为 pending 或 failed
- **THEN** 系统 MUST 以降级旧库内检索路径出题或阻断开局，并让客户端能感知「非覆盖学透」或失败原因；MUST NOT 静默声称已按要点覆盖开局

## ADDED Requirements

### Requirement: Master session records point coverage on start

学透开局在成功选定本局要点并进入闯关后，系统 MUST 更新这些要点对应当前用户的覆盖记录（至少增加 seen 计数与最近时间）。覆盖写入 MUST 在开局成功后发生，不得依赖用户是否通关。

#### Scenario: Coverage updates when master round starts

- **WHEN** 学透开局成功且本局绑定了一组要点
- **THEN** 系统 MUST 为当前用户写入或更新这些要点的覆盖记录
