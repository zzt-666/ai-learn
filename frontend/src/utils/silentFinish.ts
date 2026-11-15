import type { HistoryItem } from '../types/user'
import type { QuizSession } from '../types/quiz'
import { finishSession, updateSessionProgress } from './api'
import { loadSession, saveSession } from './storage'

function compactAnswers(answers: QuizSession['answers']) {
  return (answers || []).filter((a) => Boolean(a))
}

/**
 * Silent complete after user leaves without opening the report.
 * Do NOT call this while the user is still on the last-question explanation.
 * Safe to call repeatedly (server finish is idempotent).
 */
export async function silentFinishSession(session: QuizSession): Promise<QuizSession | null> {
  if (!session.session_id) return null
  if (session.status === 'done' || session.status === 'reporting') return session
  const answers = compactAnswers(session.answers)
  if (answers.length < session.questions.length) return null

  try {
    await updateSessionProgress(session.session_id, {
      answers,
      current_index: session.current_index,
    })
  } catch {
    // Continue; server may already have full answers.
  }

  const completed = await finishSession(session.session_id)
  const next: QuizSession = {
    ...session,
    answers,
    status: 'done',
    session_id: completed.session_id,
    exp_gained: completed.exp_gained,
    points_gained: completed.points_gained,
    pending_complete: false,
  }
  const latest = loadSession()
  if (!latest || latest.session_id === next.session_id) {
    saveSession(next)
  }
  return next
}

/**
 * Recovery: fully answered but still in_progress (e.g. leave canceled the
 * finish request). Call when entering home/history — NOT while answering.
 */
export async function settleFullyAnsweredSessions(
  items: HistoryItem[],
): Promise<boolean> {
  const ripe = items.filter(
    (item) =>
      item.status === 'in_progress' &&
      (item.answered_count ?? 0) >= (item.question_count || 0) &&
      (item.question_count || 0) > 0,
  )
  if (ripe.length === 0) return false
  await Promise.all(
    ripe.map((item) => finishSession(item.id).catch(() => null)),
  )
  return true
}
