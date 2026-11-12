import Taro from '@tarojs/taro'
import type { UserPublic } from '../types/user'
import { ApiError } from './errors'

export const API_BASE = 'http://127.0.0.1:8000'

const TOKEN_KEY = 'access_token'
const USER_KEY = 'current_user'

let loginPromise: Promise<UserPublic> | null = null

export function getToken(): string {
  try {
    return (Taro.getStorageSync(TOKEN_KEY) as string) || ''
  } catch {
    return ''
  }
}

export function getCachedUser(): UserPublic | null {
  try {
    return (Taro.getStorageSync(USER_KEY) as UserPublic) || null
  } catch {
    return null
  }
}

export function saveAuth(token: string, user: UserPublic) {
  Taro.setStorageSync(TOKEN_KEY, token)
  Taro.setStorageSync(USER_KEY, user)
}

export function clearAuth() {
  try {
    Taro.removeStorageSync(TOKEN_KEY)
    Taro.removeStorageSync(USER_KEY)
  } catch {
    // ignore
  }
}

export function isLoggedIn(): boolean {
  return Boolean(getToken())
}

export async function silentLogin(): Promise<UserPublic> {
  const loginRes = await Taro.login()
  if (!loginRes.code) {
    throw new ApiError('LOGIN_FAILED', '获取微信登录凭证失败，请重试')
  }

  const res = await Taro.request({
    url: `${API_BASE}/api/v1/auth/wechat/login`,
    method: 'POST',
    data: { code: loginRes.code },
    header: { 'Content-Type': 'application/json' },
    timeout: 15000,
  })

  if (res.statusCode < 200 || res.statusCode >= 300) {
    const body = res.data as { error_code?: string; message?: string }
    throw new ApiError(
      body?.error_code || 'LOGIN_FAILED',
      body?.message || '登录失败，请重试',
    )
  }

  const data = res.data as {
    access_token: string
    user: UserPublic
  }
  saveAuth(data.access_token, data.user)
  return data.user
}

/** 确保已登录；并发调用共用一次登录。退出后需重新调用。 */
export async function ensureLogin(force = false): Promise<UserPublic> {
  if (!force) {
    const token = getToken()
    const user = getCachedUser()
    if (token && user) return user
  }

  if (!loginPromise) {
    loginPromise = silentLogin().finally(() => {
      loginPromise = null
    })
  }
  return loginPromise
}

export function logoutLocal() {
  clearAuth()
  loginPromise = null
}
