import Taro from '@tarojs/taro'
import type { QuizSession } from '../types/quiz'

const SESSION_KEY = 'current_session'
const GUIDE_KEY = 'has_seen_guide'

export function loadSession(): QuizSession | null {
  try {
    return (Taro.getStorageSync(SESSION_KEY) as QuizSession) || null
  } catch {
    return null
  }
}

export function saveSession(session: QuizSession) {
  Taro.setStorageSync(SESSION_KEY, session)
}

export function clearSession() {
  Taro.removeStorageSync(SESSION_KEY)
}

export function hasSeenGuide(): boolean {
  try {
    return Boolean(Taro.getStorageSync(GUIDE_KEY))
  } catch {
    return false
  }
}

export function markGuideSeen() {
  Taro.setStorageSync(GUIDE_KEY, true)
}
