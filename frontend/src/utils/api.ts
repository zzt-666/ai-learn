import Taro from '@tarojs/taro'
import type { QuizPayload, ReportItem, ReportPayload } from '../types/quiz'

export const API_BASE = 'http://127.0.0.1:8000'

export class ApiError extends Error {
  error_code: string

  constructor(error_code: string, message: string) {
    super(message)
    this.error_code = error_code
  }
}

async function request<T>(
  path: string,
  options: { method?: 'GET' | 'POST'; data?: unknown } = {},
): Promise<T> {
  const { method = 'GET', data } = options
  try {
    const res = await Taro.request({
      url: `${API_BASE}${path}`,
      method,
      data,
      header: { 'Content-Type': 'application/json' },
      timeout: 90000,
    })

    if (res.statusCode >= 200 && res.statusCode < 300) {
      return res.data as T
    }

    const body = res.data as { error_code?: string; message?: string; detail?: unknown }
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
  return request<{ status: string }>('/health')
}

export function generateQuiz(payload: {
  source_text: string
  topic_name?: string
  question_count?: number
}) {
  return request<QuizPayload>('/api/v1/quiz/generate', {
    method: 'POST',
    data: payload,
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
  return request<ReportPayload>('/api/v1/report/generate', {
    method: 'POST',
    data: payload,
  })
}
