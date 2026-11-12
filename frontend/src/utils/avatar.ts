import { API_BASE } from './auth'

export function resolveAvatarUrl(url: string | null | undefined): string {
  if (!url) return ''
  if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('wxfile://')) {
    return url
  }
  return `${API_BASE}${url}`
}
