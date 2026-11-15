# Tasks

## 1. Data model & migration

- [x] 1.1 Add `knowledge_bases.mode` (nullable drill/master) and Alembic migration; verify `alembic upgrade head` on empty/dev DB
- [x] 1.2 Add `kb_questions` and `kb_question_practice` models + migration with FKs/cascade; verify tables exist and unit model import works
- [x] 1.3 Extend public KB schemas (`mode`, suggested_mode, drill counts); verify OpenAPI/schema tests or pydantic validation tests pass

## 2. Mode suggest / confirm

- [x] 2.1 Implement lightweight document feature signals → `suggested_mode`; verify fixture docs classify drill vs master reasonably in unit tests
- [x] 2.2 Add `POST /knowledge-bases/{id}/confirm-mode` locking mode and enqueueing drill-extract or master-ingest; verify API tests for lock + idempotent confirm
- [x] 2.3 Reject quiz start when mode unconfirmed; verify API returns readable `MODE_NOT_CONFIRMED` (or equivalent)

## 3. Drill extract pipeline

- [x] 3.1 Implement rule-based question splitter for single/multi/judge text items; verify markdown/PDF-text fixtures extract expected counts
- [x] 3.2 Filter image-dependent items; verify they are not inserted into `kb_questions`
- [x] 3.3 Add low-confidence model-assisted split fallback (batched); verify fallback path with mocked LLM returns structured items
- [x] 3.4 Wire document processing for drill mode to write `kb_questions` and set document status; verify integration/API status becomes ready and `GET drill-status` shows counts
- [x] 3.5 On mismatch / zero usable questions, surface warning fields; verify client-visible message and no silent mode change

## 4. Sampling, practice memory, review

- [x] 4.1 Implement unseen-first sampler by `question_count`; verify unit tests for prefer-unseen and shortfall behavior
- [x] 4.2 Persist practice rows on answer/session completion; verify next sample skips seen items
- [x] 4.3 Add `GET .../drill-status` and `POST .../reset-practice`; verify reset restores unseen pool
- [x] 4.4 Support review-round sampling when unseen empty; verify review flag required or status exposes `needs_review_prompt`

## 5. Quiz start split + lazy explanation

- [x] 5.1 Branch `generate_quiz` / task runner: drill → assemble `QuizPayload` from DB; master → existing KB RAG path; verify drill path does not call chroma retrieve
- [x] 5.2 Block drill start when empty (`DRILL_EMPTY`); verify failure response
- [x] 5.3 Lazy explanation generate+cache with source badge field; verify second call reuses cache and marks `ai`

## 6. Frontend (Taro)

- [x] 6.1 Bank detail: show mode / suggestion confirm UI calling confirm-mode; verify weapp build and manual confirm flow
- [x] 6.2 Drill start: question_count picker + call quiz task; handle empty/unconfirmed errors with toasts
- [x] 6.3 Full-coverage ConfirmModal: review / reset / cancel; verify reset then new round uses unseen again
- [x] 6.4 Show explanation source badge on quiz/review UI when field present; verify build succeeds

## 7. Integration checks

- [x] 7.1 Run backend pytest subset for knowledge-drill/quiz split and fix failures until green
- [ ] 7.2 Manual: import formal text question bank → confirm drill → multi-round unseen then review prompt
- [ ] 7.3 Manual: confirm master on a notes doc → start still uses RAG generation

## Workflow follow-up

- Archive `optimize-kb-drill-mode` after review when P0 behavior is accepted.
- Consider archiving or finishing remaining manual item on `add-private-knowledge-bases` if still open.
- P1 学透章节地图另开 change，不混入本任务勾选。
