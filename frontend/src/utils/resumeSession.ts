import Taro from '@tarojs/taro'
import type { QuizSession } from '../types/quiz'
import type { SessionDetail } from '../types/user'
import { ApiError, createSession, fetchSession, retryHistory } from './api'
import { saveSession } from './storage'

function detailToSession(detail: SessionDetail): QuizSession {
  const answers = [...(detail.answers || [])]
  return {
    topic_name: detail.topic_name,
    source_text: detail.source_text,
    questions: detail.questions,
    answers,
    current_index: detail.current_index || 0,
    report: detail.report ?? null,
    status:
      detail.status === 'completed'
        ? 'done'
        : detail.report
          ? 'reporting'
          : 'answering',
    knowledge_base_id: detail.knowledge_base_id ?? null,
    source_session_id: detail.source_session_id ?? null,
    session_id: detail.id,
    exp_gained: detail.exp_gained ?? null,
    points_gained: detail.points_gained ?? null,
  }
}

/** Load unfinished session from server and open quiz (no regenerate). */
export async function resumeUnfinishedSession(sessionId: number): Promise<void> {
  const detail = await fetchSession(sessionId)
  if (detail.status === 'completed') {
    Taro.navigateTo({ url: `/pages/history/report?id=${sessionId}` })
    return
  }
  const session = detailToSession(detail)
  saveSession(session)
  Taro.navigateTo({ url: '/pages/quiz/index' })
}

/** Retry a completed history item: shuffle + create a new server session. */
export async function startRetryFromHistory(sourceSessionId: number): Promise<void> {
  const payload = await retryHistory(sourceSessionId)
  const created = await createSession({
    topic_name: payload.topic_name,
    source_text: payload.source_text,
    questions: payload.questions,
    answers: [],
    current_index: 0,
    source_session_id: payload.source_session_id,
  })
  const session: QuizSession = {
    topic_name: payload.topic_name,
    source_text: payload.source_text,
    questions: payload.questions,
    answers: [],
    current_index: 0,
    report: null,
    status: 'answering',
    source_session_id: payload.source_session_id,
    session_id: created.session_id,
  }
  saveSession(session)
  Taro.redirectTo({ url: '/pages/quiz/index' })
}

export function toastResumeError(err: unknown, fallback = '恢复失败') {
  Taro.showToast({
    title: err instanceof ApiError ? err.message : fallback,
    icon: 'none',
  })
}
