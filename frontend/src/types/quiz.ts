export type QuestionType = 'single' | 'multiple' | 'boolean'

export interface Question {
  id: string
  type: QuestionType
  stem: string
  options: string[]
  answer_indexes: number[]
  explanation: string
}

export interface QuizPayload {
  topic_name: string
  questions: Question[]
}

export interface UserAnswer {
  question_id: string
  selected_indexes: number[]
  is_correct: boolean
}

export interface ReportItem {
  question_id: string
  type: QuestionType
  stem: string
  options: string[]
  answer_indexes: number[]
  selected_indexes: number[]
  is_correct: boolean
  explanation: string
}

export interface WrongReviewItem {
  question_id: string
  type: QuestionType
  stem: string
  brief_reason: string
}

export interface ReportPayload {
  summary_points: string[]
  accuracy: number
  correct_count: number
  wrong_count: number
  wrong_review: WrongReviewItem[]
  weaknesses: string[]
}

export interface QuizSession {
  topic_name: string
  source_text: string
  questions: Question[]
  answers: UserAnswer[]
  current_index: number
  report?: ReportPayload | null
  status: 'answering' | 'reporting' | 'done'
}
