import Taro from '@tarojs/taro'

const PENDING_TEXT_KEY = 'pending_source_text'

export function setPendingSourceText(text: string) {
  Taro.setStorageSync(PENDING_TEXT_KEY, text)
}

export function takePendingSourceText(): string {
  try {
    const text = String(Taro.getStorageSync(PENDING_TEXT_KEY) || '')
    Taro.removeStorageSync(PENDING_TEXT_KEY)
    return text
  } catch {
    return ''
  }
}
