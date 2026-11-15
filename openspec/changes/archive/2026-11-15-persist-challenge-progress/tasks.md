# Tasks

## 1. Data model & session APIs

- [x] 1.1 Add Alembic migration for `quiz_sessions`: `status`, `current_index`, optional `knowledge_base_id`, `updated_at`; relax nullability on completion-only fields; backfill existing rows as `completed` — verify migration upgrade/downgrade on a local DB
- [x] 1.2 Implement `POST /api/v1/sessions` to create `in_progress` session with questions/topic/source — verify API test creates owned row and returns `session_id`
- [x] 1.3 Implement `PATCH /api/v1/sessions/{id}/progress` (answers + current_index, ownership) — verify partial answers persist and foreign user gets 404
- [x] 1.4 Implement `GET /api/v1/sessions/{id}` (or history detail) returning full resume payload for owner — verify questions, answers, and index round-trip
- [x] 1.5 Extend `POST /api/v1/sessions/complete` (and/or `POST .../finish`) for idempotent `in_progress`→`completed` with reward settle once; optional server-side report generate when report missing — verify double-call does not double EXP and completed row has report or recoverable failure state

## 2. History list & silent completion

- [x] 2.1 Update history list/detail serializers to emit real `status` (`in_progress` | `completed`), `answered_count` / `question_count`, and include unfinished sessions ordered by recency — verify unfinished appears with progress fields and completed still works
- [x] 2.2 Gate report/retry endpoints: unfinished MUST NOT return a fake completed report; completed report path unchanged — verify status-specific responses in tests
- [x] 2.3 Add service path for “all answers present → finish + silent report” reusable by finish API — verify unit/integration test covers silent complete without client report body
- [x] 2.4 Support listing unfinished with limit (e.g. `status=in_progress&limit=3`) for home — verify API returns at most N unfinished in shared sort order

## 3. Front-end persist & resume

- [x] 3.1 On generate success, create server session before entering quiz; store `session_id` on local session — verify enter is blocked or warned if create fails (prefer block)
- [x] 3.2 Sync progress from quiz page after each graded answer and on hide; map API helpers in `utils/api.ts` — verify Storage and server stay aligned after answer + leave
- [x] 3.3 History: show「未完成」vs「已通关」; unfinished tap restores session and opens quiz at saved index — verify resume does not regenerate questions
- [x] 3.4 Home unfinished section: max 3 items, empty tip when none, right-side progress bar (`answered_count/question_count`), tap to resume; refresh on `useDidShow` from same unfinished source as history — verify >3 only fully listed on history and home stays ≤3
- [x] 3.5 When all questions answered, leaving quiz without opening report triggers finish/silent complete;「查看报告」still opens report (may already be ready) — verify history shows completed with viewable report after leave-without-report
- [x] 3.6 After resume-complete from history, returning to home removes that session from the unfinished preview — verify home and history unfinished sets stay in sync

## 4. Regression & integration

- [x] 4.1 Extend `backend/tests/test_sessions_history.py` (and related) for create/progress/resume/silent-finish/idempotent complete/home limit — verify suite passes
- [x] 4.2 Smoke: new quiz while another unfinished exists keeps both; retry of completed session still creates a distinct new session — verify via API tests or manual checklist notes in PR
