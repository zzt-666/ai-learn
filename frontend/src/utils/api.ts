import Taro from '@tarojs/taro'
import type { QuizPayload, ReportItem, ReportPayload } from '../types/quiz'
import type {
  CompleteSessionResponse,
  HistoryDetail,
  HistoryItem,
  RetrySessionPayload,
  UserPublic,
} from '../types/user'
import { API_BASE, clearAuth, ensureLogin, getToken, saveAuth } from './auth'
import { ApiError } from './errors'

export { API_BASE, ApiError }

type Method = 'GET' | 'POST' | 'PATCH'

async function rawRequest<T>(
  path: string,
  options: {
    method?: Method
    data?: unknown
    auth?: boolean
    retried?: boolean
  } = {},
): Promise<T> {
  const { method = 'GET', data, auth = true, retried = false } = options
  const header: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (auth) {
    const token = getToken()
    if (token) header.Authorization = `Bearer ${token}`
  }

  try {
    const res = await Taro.request({
      url: `${API_BASE}${path}`,
      method,
      data,
      header,
      timeout: 90000,
    })

    if (res.statusCode >= 200 && res.statusCode < 300) {
      return res.data as T
    }

    if (res.statusCode === 401 && auth && !retried) {
      clearAuth()
      await ensureLogin(true)
      return rawRequest<T>(path, { method, data, auth, retried: true })
    }

    const body = res.data as { error_code?: string; message?: string }
    throw new ApiError(
      body?.error_code || 'REQUEST_FAILED',
      body?.message || `请求失败（${res.statusCode}）`,
    )
  } catch (err) {
    if (err instanceof ApiError) throw err
    throw new ApiError('UPSTREAM_TIMEOUT', '网络异常或超时，请稍后重试')
  }
}

export function healthCheck() {
  return rawRequest<{ status: string }>('/health', { auth: false })
}

export function fetchMe() {
  return rawRequest<UserPublic>('/api/v1/me')
}

export function updateNickname(nickname: string) {
  return rawRequest<UserPublic>('/api/v1/me', {
    method: 'PATCH',
    data: { nickname },
  }).then((user) => {
    const token = getToken()
    if (token) saveAuth(token, user)
    return user
  })
}

export async function uploadAvatar(filePath: string): Promise<UserPublic> {
  const doUpload = async () => {
    const token = getToken()
    const res = await Taro.uploadFile({
      url: `${API_BASE}/api/v1/me/avatar`,
      filePath,
      name: 'file',
      header: token ? { Authorization: `Bearer ${token}` } : {},
    })
    const body = typeof res.data === 'string' ? JSON.parse(res.data) : res.data
    if (res.statusCode >= 200 && res.statusCode < 300) {
      const user = body as UserPublic
      if (token) saveAuth(token, user)
      return user
    }
    throw new ApiError(
      body?.error_code || 'REQUEST_FAILED',
      body?.message || `上传失败（${res.statusCode}）`,
    )
  }

  try {
    return await doUpload()
  } catch (err) {
    if (err instanceof ApiError && err.error_code === 'UNAUTHORIZED') {
      clearAuth()
      await ensureLogin(true)
      return doUpload()
    }
    if (err instanceof ApiError) throw err
    throw new ApiError('UPLOAD_FAILED', '头像上传失败，请重试')
  }
}

export type QuizTaskStatus =
  | 'pending'
  | 'running'
  | 'succeeded'
  | 'failed'
  | 'cancelled'

export interface QuizTaskCreated {
  task_id: number
  status: QuizTaskStatus
}

export interface QuizTaskPollResult {
  task_id: number
  status: QuizTaskStatus
  topic_name?: string | null
  questions?: QuizPayload['questions'] | null
  error_message?: string | null
  created_at?: string | null
  finished_at?: string | null
}

/** Sync generate (legacy). Prefer createQuizTask + getQuizTask. */
export function generateQuiz(payload: {
  source_text: string
  topic_name?: string
  question_count?: number
}) {
  return rawRequest<QuizPayload>('/api/v1/quiz/generate', {
    method: 'POST',
    data: payload,
  })
}

export function createQuizTask(payload: {
  source_text: string
  topic_name?: string
  question_count?: number
}) {
  return rawRequest<QuizTaskCreated>('/api/v1/quiz/tasks', {
    method: 'POST',
    data: payload,
  })
}

export function getQuizTask(taskId: number) {
  return rawRequest<QuizTaskPollResult>(`/api/v1/quiz/tasks/${taskId}`)
}

export function cancelQuizTask(taskId: number) {
  return rawRequest<QuizTaskPollResult>(`/api/v1/quiz/tasks/${taskId}/cancel`, {
    method: 'POST',
  })
}

export function generateReport(payload: {
  topic_name: string
  source_text_excerpt: string
  correct_count: number
  wrong_count: number
  accuracy: number
  items: ReportItem[]
}) {
  return rawRequest<ReportPayload>('/api/v1/report/generate', {
    method: 'POST',
    data: payload,
  })
}

export function completeSession(payload: {
  topic_name: string
  source_text: string
  questions: unknown[]
  answers: unknown[]
  report: ReportPayload
  source_session_id?: number | null
}) {
  return rawRequest<CompleteSessionResponse>('/api/v1/sessions/complete', {
    method: 'POST',
    data: payload,
  }).then((data) => {
    const token = getToken()
    if (token) saveAuth(token, data.user)
    return data
  })
}

export function fetchHistory(limit = 50) {
  return rawRequest<HistoryItem[]>(`/api/v1/history?limit=${limit}`)
}

export function fetchHistoryDetail(id: number) {
  return rawRequest<HistoryDetail>(`/api/v1/history/${id}`)
}

export function fetchHistoryReport(id: number) {
  return rawRequest<ReportPayload>(`/api/v1/history/${id}/report`)
}

export function retryHistory(id: number) {
  return rawRequest<RetrySessionPayload>(`/api/v1/history/${id}/retry`, {
    method: 'POST',
  })
}
