export interface UserPublic {
  id: number
  nickname: string
  avatar_url: string | null
  exp: number
  points: number
  level: number
  completed_count: number
  exp_to_next_level: number
  level_progress: number
}

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: UserPublic
}

export interface HistoryItem {
  id: number
  topic_name: string
  finished_at: string
  accuracy: number
  question_count: number
  exp_gained: number
  points_gained: number
  status: string
}

export interface HistoryDetail {
  id: number
  topic_name: string
  finished_at: string
  accuracy: number
  correct_count: number
  wrong_count: number
  question_count: number
  exp_gained: number
  points_gained: number
  status: string
  source_session_id: number | null
}

export interface RetrySessionPayload {
  topic_name: string
  source_text: string
  questions: import('./quiz').Question[]
  source_session_id: number
}

export interface CompleteSessionResponse {
  session_id: number
  exp_gained: number
  points_gained: number
  user: UserPublic
}
