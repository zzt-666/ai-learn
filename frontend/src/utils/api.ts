import Taro from '@tarojs/taro'
import type {
  Question,
  QuizPayload,
  ReportItem,
  ReportPayload,
  UserAnswer,
} from '../types/quiz'
import type {
  CompleteSessionResponse,
  HistoryDetail,
  HistoryItem,
  RetrySessionPayload,
  SessionDetail,
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
  knowledge_base_id?: number
  drill_round?: 'review' | null
}) {
  return rawRequest<QuizTaskCreated>('/api/v1/quiz/tasks', {
    method: 'POST',
    data: payload,
  })
}

export type KnowledgeBaseMode = 'drill' | 'master'

export interface KnowledgeBaseItem {
  id: number
  name: string
  description?: string | null
  mode?: KnowledgeBaseMode | null
  suggested_mode?: KnowledgeBaseMode | null
  mode_confirmed_at?: string | null
  ready_document_count: number
  document_count: number
  active_question_count?: number
  created_at?: string | null
  updated_at?: string | null
}

export interface KnowledgeDocumentItem {
  id: number
  knowledge_base_id: number
  filename: string
  content_type: string
  size_bytes: number
  status: 'pending' | 'processing' | 'awaiting_mode' | 'ready' | 'failed'
  error_message?: string | null
  chunk_count: number
  created_at?: string | null
  updated_at?: string | null
}

export interface DrillStatusItem {
  knowledge_base_id: number
  mode?: KnowledgeBaseMode | null
  suggested_mode?: KnowledgeBaseMode | null
  mode_confirmed: boolean
  total_questions: number
  unseen_questions: number
  needs_review_prompt: boolean
  needs_empty_drill_prompt?: boolean
  auto_switched_to_master?: boolean
  warning?: string | null
}

export type MasterMapStatus = 'pending' | 'ready' | 'failed'

export interface MasterStatusItem {
  knowledge_base_id: number
  map_status?: MasterMapStatus | null
  total_points: number
  covered_points: number
  uncovered_points: number
  needs_review_prompt: boolean
  warning?: string | null
  error_message?: string | null
}

export function fetchKnowledgeBases() {
  return rawRequest<KnowledgeBaseItem[]>('/api/v1/knowledge-bases')
}

export function createKnowledgeBase(payload: { name: string; description?: string }) {
  return rawRequest<KnowledgeBaseItem>('/api/v1/knowledge-bases', {
    method: 'POST',
    data: payload,
  })
}

export function updateKnowledgeBase(
  id: number,
  payload: { name?: string; description?: string | null },
) {
  return rawRequest<KnowledgeBaseItem>(`/api/v1/knowledge-bases/${id}`, {
    method: 'PATCH',
    data: payload,
  })
}

export function deleteKnowledgeBase(id: number) {
  return rawRequest<{ ok: boolean }>(`/api/v1/knowledge-bases/${id}`, {
    method: 'DELETE',
  })
}

export function confirmKnowledgeBaseMode(
  id: number,
  mode: KnowledgeBaseMode,
  force = true,
) {
  return rawRequest<KnowledgeBaseItem>(
    `/api/v1/knowledge-bases/${id}/confirm-mode`,
    {
      method: 'POST',
      data: { mode, force },
    },
  )
}

export function fetchQuestionExplanation(kbId: number, questionId: number) {
  return rawRequest<{
    question_id: number
    explanation: string
    explanation_source: 'source' | 'ai' | 'none'
  }>(`/api/v1/knowledge-bases/${kbId}/questions/${questionId}/explanation`, {
    method: 'POST',
  })
}

export function fetchDrillStatus(kbId: number) {
  return rawRequest<DrillStatusItem>(
    `/api/v1/knowledge-bases/${kbId}/drill-status`,
  )
}

export function resetDrillPractice(kbId: number) {
  return rawRequest<{ ok: boolean }>(
    `/api/v1/knowledge-bases/${kbId}/reset-practice`,
    { method: 'POST' },
  )
}

export function fetchMasterStatus(kbId: number) {
  return rawRequest<MasterStatusItem>(
    `/api/v1/knowledge-bases/${kbId}/master-status`,
  )
}

export function rebuildMasterMap(kbId: number) {
  return rawRequest<MasterStatusItem>(
    `/api/v1/knowledge-bases/${kbId}/master-map/rebuild`,
    { method: 'POST' },
  )
}

export function resetMasterCoverage(kbId: number) {
  return rawRequest<{ ok: boolean }>(
    `/api/v1/knowledge-bases/${kbId}/reset-master-coverage`,
    { method: 'POST' },
  )
}

export function fetchKnowledgeDocuments(kbId: number) {
  return rawRequest<KnowledgeDocumentItem[]>(
    `/api/v1/knowledge-bases/${kbId}/documents`,
  )
}

export function fetchKnowledgeDocument(kbId: number, docId: number) {
  return rawRequest<KnowledgeDocumentItem>(
    `/api/v1/knowledge-bases/${kbId}/documents/${docId}`,
  )
}

export function deleteKnowledgeDocument(kbId: number, docId: number) {
  return rawRequest<{ ok: boolean }>(
    `/api/v1/knowledge-bases/${kbId}/documents/${docId}`,
    { method: 'DELETE' },
  )
}

export async function uploadKnowledgeDocument(
  kbId: number,
  filePath: string,
  fileName?: string,
): Promise<KnowledgeDocumentItem> {
  const doUpload = async () => {
    const token = getToken()
    const res = await Taro.uploadFile({
      url: `${API_BASE}/api/v1/knowledge-bases/${kbId}/documents`,
      filePath,
      name: 'file',
      fileName,
      header: token ? { Authorization: `Bearer ${token}` } : {},
    })
    const body = typeof res.data === 'string' ? JSON.parse(res.data) : res.data
    if (res.statusCode >= 200 && res.statusCode < 300) {
      return body as KnowledgeDocumentItem
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
    throw new ApiError('UPLOAD_FAILED', '文档上传失败，请重试')
  }
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

export function createSession(payload: {
  topic_name: string
  source_text: string
  questions: Question[]
  answers?: UserAnswer[]
  current_index?: number
  knowledge_base_id?: number | null
  source_session_id?: number | null
}) {
  return rawRequest<{ session_id: number; status: string }>('/api/v1/sessions', {
    method: 'POST',
    data: payload,
  })
}

export function updateSessionProgress(
  sessionId: number,
  payload: { answers: UserAnswer[]; current_index: number },
) {
  return rawRequest<SessionDetail>(`/api/v1/sessions/${sessionId}/progress`, {
    method: 'PATCH',
    data: payload,
  })
}

export function fetchSession(sessionId: number) {
  return rawRequest<SessionDetail>(`/api/v1/sessions/${sessionId}`)
}

export function finishSession(sessionId: number) {
  return rawRequest<CompleteSessionResponse>(
    `/api/v1/sessions/${sessionId}/finish`,
    { method: 'POST' },
  ).then((data) => {
    const token = getToken()
    if (token) saveAuth(token, data.user)
    return data
  })
}

export function completeSession(payload: {
  topic_name: string
  source_text: string
  questions: unknown[]
  answers: unknown[]
  report?: ReportPayload | null
  source_session_id?: number | null
  session_id?: number | null
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

export function fetchHistory(
  limit = 50,
  opts?: { status?: 'in_progress' | 'completed' },
) {
  const params = new URLSearchParams({ limit: String(limit) })
  if (opts?.status) params.set('status', opts.status)
  return rawRequest<HistoryItem[]>(`/api/v1/history?${params.toString()}`)
}

export function fetchHistoryDetail(id: number) {
  return rawRequest<HistoryDetail>(`/api/v1/history/${id}`)
}

export type HistoryReportResult =
  | { status: 'ready'; report: ReportPayload }
  | { status: 'pending'; report?: null }

export function fetchHistoryReport(id: number) {
  return rawRequest<HistoryReportResult>(`/api/v1/history/${id}/report`)
}

export function retryHistory(id: number) {
  return rawRequest<RetrySessionPayload>(`/api/v1/history/${id}/retry`, {
    method: 'POST',
  })
}
