# Design

## Context

- 私有知识库 CRUD、文档入库、Chroma RAG 与强制库开局已在 `add-private-knowledge-bases` 落地（见该 change 与 `docs/知识库刷题优化需求分析文档.md`）。
- 现状强制库开局：`kb_retrieve` Top-K → `QUIZ_SYSTEM_KB` 生成；对正式题库 PDF 覆盖差。
- 动机与范围见 `proposal.md`；行为契约见本 change 的 `specs/knowledge-drill`、`specs/quiz-generation`。

## Goals / Non-Goals

**Goals:**

- 库级 `mode`（drill/master）+ 建议/确认；刷题拆题进 MySQL、抽题、已刷、复习轮、解析懒生成。
- 强制开局按 mode 分流；学透路径复用现有 RAG，本变更不重做章节地图。
- 与现有 quiz 载荷字段兼容，答题/报告尽量复用。

**Non-Goals:**

- 学透 P1（结构切分、要点地图、块轮转）；错题本完整产品；OSS；独立 Rerank；图片题；填空/简答刷题。

## Decisions

### 1. 数据模型

| 表/字段 | 要点 |
|---------|------|
| `knowledge_bases.mode` | `drill` \| `master`；可空表示未确认；确认后锁定 |
| `knowledge_bases.mode_confirmed_at` | 可选，审计 |
| `kb_questions` | `id`, `knowledge_base_id`, `document_id`, `qtype`(`single`/`multi`/`judge`), `stem`, `options_json`, `answer_indices_json`, `explanation`, `explanation_source`(`source`/`ai`/`none`), `is_active`, 时间戳 |
| `kb_question_practice` | `user_id`, `knowledge_base_id`, `question_id`, `last_seen_at`, `correct_count`, `wrong_count`；唯一键 `(user_id, question_id)` |

删除库/文档时级联停用或删除对应题目与练习记录。

**备选**：题目只进 Chroma → 否（刷题要精确抽题与已刷，不靠 ANN）。

### 2. 入库分流

```text
upload → 既有 document pending/processing
  if kb.mode == master (or unset but will confirm master):
    现有 parse/split/embed/chroma（不变）
  if kb.mode == drill:
    文本提取 → 规则拆题 → 低置信度则小模型补拆
    → 过滤图片题/非三种题型 → 写入 kb_questions
    → document ready（以「可抽题数>0」或「拆题完成且允许0题+警告」为准，产品取：0 题 ready 但开局阻断）
  mode 未确认：
    先做轻量特征检测 → suggested_mode；用户确认 mode 后再跑对应重处理或首次处理
```

新建库：导入首份文档后出建议；确认 drill 后再拆题（若已按 master 向量化，确认改 drill 时触发拆题任务；改 master 时触发向量入库）。为降复杂度：**创建时先选/确认模式，再上传**；若先上传后确认，则确认时触发对应 pipeline（实现选后者更贴「建议来自文档」）。

**决策**：上传完成后异步产出 `suggested_mode`；用户 `POST .../confirm-mode` 后触发 drill 拆题或 master 向量化（未确认前文档可显示「待确认模式」）。

### 3. 拆题策略

- 规则：题号/选项 A-D/答案行等启发式；输出置信度。
- 低于阈值：按块调用现有 DeepSeek，structured output 拆题（限批、限字符）。
- 不入库图片题；选项必须纯文本。

### 4. 开局分流

```text
POST /quiz/tasks + knowledge_base_id + question_count:
  load kb, assert owner, mode confirmed
  if master → 现有 gather_research_context KB forced + generate_quiz
  if drill:
    sample questions (unseen first; review flag if unseen empty → 前端应先走复习轮确认)
    map to QuizPayload questions
    skip embedding retrieve / skip LLM generate for stems
    optional: explanations filled later via lazy API
```

复习轮：请求带 `drill_round=review` 或先 `GET .../drill-status` 发现 `unseen=0` 由前端弹层后再带 flag。

### 5. API 增量（草图）

| 方法 | 路径 | 作用 |
|------|------|------|
| PATCH | `/knowledge-bases/{id}` | 可含 mode（仅未确认或显式「改模式」且二次确认） |
| POST | `/knowledge-bases/{id}/confirm-mode` | `{ mode }` 锁定并触发 pipeline |
| GET | `/knowledge-bases/{id}/drill-status` | 总题数、未刷、建议 |
| POST | `/knowledge-bases/{id}/reset-practice` | 清空已刷 |
| POST | `/quiz/tasks` | drill 时组装题；可选 `drill_round` |
| POST | `/knowledge-bases/{id}/questions/{qid}/explanation` | 懒生成解析 |

错误：`MODE_NOT_CONFIRMED`、`DRILL_EMPTY`、`MODE_MISMATCH_DOC`。

### 6. 前端

- 详情：模式徽章、建议确认条、题量选择、刷完 ConfirmModal（复习/重置/取消）。
- 解析角标：原文 / AI。
- 学透开局文案保持「开始闯关」；刷题为抽题开局。

### 7. 测试

- 规则拆题夹具（规范 md 题库）；过滤图片题。
- 抽题优先未刷；复习轮；重置。
- 开局分流：drill 不调 chroma retrieve；master 仍走 KB generate。
- 越权与空库阻断。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| 乱版式 PDF 拆题差 | 规则+模型补拆；失败提醒换文档；不做 OCR |
| 用户先建库后改模式成本高 | 改模式需确认；改 drill 重跑拆题、改 master 重跑向量 |
| 解析懒生成延迟 | 答题页先出「生成中」；失败仍可无解析通关 |
| 与未归档 KB change 并存 | 本 change 依赖 KB 表已存在；迁移只 ADD 列/新表 |

## Migration Plan

1. Alembic：`mode` 列（默认 `NULL` 未确认）；`kb_questions`；`kb_question_practice`。
2. 已有知识库：`mode=NULL`，首次进入详情引导确认；确认前禁止开局或仅允许确认后开局。
3. 回滚：忽略 drill API；开局若 mode=drill 可临时拒绝并提示升级客户端。

## Open Questions

- 复习轮是否默认错题优先：实现期默认「随机/久远优先」，错题优先随 P2 错题本。
- 规则/模型置信度具体阈值：实现时用夹具标定，不改规格语义。
