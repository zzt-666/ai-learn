# Design

## Context

See `proposal.md` for motivation. Today:

- Front-end keeps the active round only in Taro Storage (`current_session`); `pages/generate` overwrites it on each successful start.
- Server writes `quiz_sessions` only on `POST /api/v1/sessions/complete`, which requires a full answer set **and** a `report`.
- `HistoryItem.status` already exists on the API model but is always `"completed"`.
- `ensureReportBuilt` already can finish report + complete after the report page unmounts, but nothing starts that pipeline if the user never navigates to report after the last question.

## Goals / Non-Goals

**Goals:**

- Server-authoritative in-progress sessions (questions + answers + cursor).
- Resume UX via history and a home unfinished preview (max 3, progress bar, empty tip) that stays in sync with history unfinished.
- Auto-complete + silent report when all questions are answered even if report UI is skipped.
- Keep existing complete/report contracts usable; extend rather than replace.

**Non-Goals:**

- Changing quiz generation / knowledge-base sampling rules.
- Multi-device live sync UX (save/resume is enough; no real-time collaboration).
- Abandon/delete unfinished sessions UI (may add later; not required for this change).
- Changing EXP/积分公式.

## Decisions

### 1. Extend `quiz_sessions` with lifecycle status instead of a separate table

- Add `status`: `in_progress` | `completed` (string, indexed).
- Make completion-only columns nullable or defaulted while `in_progress`: `correct_count`, `wrong_count`, `accuracy`, `exp_gained`, `points_gained`, `report_json`, `finished_at`.
- Always store `questions_json`, `answers_json` (partial ok), `topic_name`, `source_text`, `question_count`, optional `knowledge_base_id`, `current_index`, `source_session_id`, `updated_at`.

**Why:** One list endpoint already maps to `quiz_sessions`; history already has a `status` field. Alternatives considered: separate `quiz_session_drafts` table (cleaner nullability, more join/list complexity) — rejected for MVP simplicity.

### 2. Session APIs

| Action | Approach |
|--------|----------|
| Create on enter quiz | `POST /api/v1/sessions` after generate succeeds → returns `session_id`; client stores it on local session |
| Save progress | `PATCH /api/v1/sessions/{id}/progress` with `answers`, `current_index` (ownership check) |
| Load for resume | `GET /api/v1/sessions/{id}` or reuse history detail expanded for in_progress |
| Silent / normal complete | Keep `POST /api/v1/sessions/complete` but allow `session_id` to update the same row (idempotent transition `in_progress` → `completed`); still accept report in body **or** trigger server-side report generation when completing without client report |

**Silent complete path:** Client (or a thin leave hook) calls a dedicated `POST /api/v1/sessions/{id}/finish` when `len(answers) == question_count` and user leaves without opening report. Server grades, settles rewards once, sets `status=completed`, and enqueues/runs report generation if `report_json` empty. History report endpoint returns 202/pending payload or blocks until ready — prefer: generate synchronously if cheap enough today (existing `/report/generate`), else store `report_status=pending` and let history poll/retry. **Default for this change:** reuse existing generate-report service on the finish path (same as client `ensureReportBuilt`), so history usually has a report immediately; on generate failure keep session `completed` with empty/placeholder report and allow later regenerate.

### 3. History list semantics

- `GET /api/v1/history` returns both `in_progress` and `completed`, ordered by `updated_at` / `finished_at` desc (in_progress use `updated_at`).
- Unfinished items: include `answered_count` (and `question_count`) for progress UI; accuracy/rewards may be `0` or omitted; UI shows「未完成」+「继续」; tap → restore local session from server payload → `pages/quiz`.
- Completed: unchanged「已通关」→ report.
- History page lists **all** unfinished (no 3-item cap).

### 3b. Home unfinished preview

- Home has a dedicated unfinished section fed by the **same** unfinished set/order as history (e.g. `GET /api/v1/history?status=in_progress&limit=3` or client filter of the shared list).
- Cap: **at most 3** rows on home; overflow only on history.
- Each row: topic + right-side progress bar = `answered_count / question_count`.
- Empty: show tip copy only (no fake rows).
- Refresh on `useDidShow` so resume-complete from history removes the row from home on return.

### 4. Client progress sync

- On each graded answer and on `goNext` index change: debounce PATCH progress (e.g. 300ms) plus flush on page hide (`useDidHide` / `onHide`).
- On generate success: create server session before navigating to quiz; if create fails, still allow local play but warn that resume may be unavailable (or block enter — prefer **block enter** so we never “waste” a round that cannot be resumed).
- Local Storage remains hot cache keyed by `session_id`.

### 5. Last-question leave = complete

- Today last question’s CTA only sets `status: 'reporting'` when user taps「查看报告」.
- Additionally: when `answers.length === questions.length`, leaving quiz page (`useDidHide` / unload) or navigating home MUST call finish/complete pipeline (idempotent). Tapping「查看报告」still goes to report page; report may already exist from silent finish.

### 6. New quiz vs old unfinished

- Creating a new session never deletes other `in_progress` rows.
- Local `current_session` points at the active round only; previous unfinished remain recoverable from history.

## Risks / Trade-offs

- [Nullable columns on `quiz_sessions`] → Mitigation: app-layer invariants; list/detail serializers branch on `status`.
- [Duplicate reward if finish + complete both called] → Mitigation: single transition guard (`status` already `completed` → return existing rewards, no second apply).
- [Report generate fails on silent finish] → Mitigation: mark completed anyway; expose retry on history report view; optional placeholder summary from local grading stats.
- [Many abandoned in_progress rows] → Mitigation: out of scope delete UI; may later TTL — document as follow-up.
- [Debounced PATCH loses last answer on kill] → Mitigation: flush on hide; sync after each submit before UI advances when possible.

## Migration Plan

1. Alembic: add `status`, `current_index`, `knowledge_base_id`, `updated_at`; relax nullability on completion fields; backfill existing rows `status='completed'`, `updated_at=finished_at`.
2. Deploy API (create/progress/finish + history filter) before or with client that depends on them.
3. Ship mini-program: create session on start, PATCH progress, history resume, silent finish.
4. Rollback: client can ignore unfinished; old complete path still works. DB columns remain compatible if defaults set.

## Open Questions

- Exact empty-state / badge copy（「未完成」vs「进行中」、无未完成时的提示语文案）— product polish; behavior is fixed above.
