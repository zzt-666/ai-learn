import type { QuizSession, ReportPayload } from '../types/quiz'
import { ApiError, completeSession, generateReport } from './api'
import { summarize } from './grading'
import { loadSession, saveSession } from './storage'

let inFlight: Promise<QuizSession> | null = null
let inFlightKey: string | null = null

function sessionKey(s: QuizSession): string {
  return [
    s.topic_name,
    s.answers.length,
    s.answers.map((a) => `${a.question_id}:${a.is_correct ? 1 : 0}`).join(','),
  ].join('|')
}

/** Build report items payload for the generate API. */
export function buildReportItems(s: QuizSession) {
  return s.questions.map((q, i) => {
    const a = s.answers[i]
    return {
      question_id: q.id,
      type: q.type,
      stem: q.stem,
      options: q.options,
      answer_indexes: q.answer_indexes,
      selected_indexes: a?.selected_indexes || [],
      is_correct: Boolean(a?.is_correct),
      explanation: q.explanation,
    }
  })
}

/**
 * Generate AI report + complete session. Survives report page unmount so history
 * can still receive the result if the user leaves early.
 */
export function ensureReportBuilt(session: QuizSession): Promise<QuizSession> {
  const latest = loadSession()
  const base = latest && sessionKey(latest) === sessionKey(session) ? latest : session

  if (base.report && !base.pending_complete) {
    return Promise.resolve(base)
  }

  if (base.report && base.pending_complete) {
    return completeOnly(base)
  }

  const key = sessionKey(base)
  if (inFlight && inFlightKey === key) {
    return inFlight
  }

  inFlightKey = key
  inFlight = (async () => {
    const stats = summarize(base.answers)
    const report: ReportPayload = await generateReport({
      topic_name: base.topic_name,
      source_text_excerpt: base.source_text.slice(0, 2000),
      correct_count: stats.correct_count,
      wrong_count: stats.wrong_count,
      accuracy: stats.accuracy,
      items: buildReportItems(base),
    })

    let next: QuizSession = {
      ...base,
      report,
      status: 'done',
      pending_complete: true,
    }
    saveSession(next)

    try {
      const completed = await completeSession({
        topic_name: next.topic_name,
        source_text: next.source_text,
        questions: next.questions,
        answers: next.answers,
        report,
        source_session_id: next.source_session_id ?? null,
      })
      next = {
        ...next,
        session_id: completed.session_id,
        exp_gained: completed.exp_gained,
        points_gained: completed.points_gained,
        pending_complete: false,
      }
      saveSession(next)
    } catch {
      // Keep report; UI can retry complete.
      saveSession(next)
    }
    return next
  })()
    .catch((err) => {
      throw err instanceof ApiError
        ? err
        : new ApiError('GENERATE_FAILED', '报告生成失败，请重试')
    })
    .finally(() => {
      inFlight = null
      inFlightKey = null
    })

  return inFlight
}

function completeOnly(session: QuizSession): Promise<QuizSession> {
  if (!session.report) return Promise.resolve(session)
  const key = `complete:${sessionKey(session)}`
  if (inFlight && inFlightKey === key) return inFlight

  inFlightKey = key
  inFlight = (async () => {
    const completed = await completeSession({
      topic_name: session.topic_name,
      source_text: session.source_text,
      questions: session.questions,
      answers: session.answers,
      report: session.report!,
      source_session_id: session.source_session_id ?? null,
    })
    const next: QuizSession = {
      ...session,
      session_id: completed.session_id,
      exp_gained: completed.exp_gained,
      points_gained: completed.points_gained,
      pending_complete: false,
    }
    saveSession(next)
    return next
  })().finally(() => {
    inFlight = null
    inFlightKey = null
  })

  return inFlight
}

export function isReportBuildInFlight(): boolean {
  return inFlight != null
}
