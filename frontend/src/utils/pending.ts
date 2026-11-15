import Taro from '@tarojs/taro'

const PENDING_TEXT_KEY = 'pending_source_text'
const PENDING_KB_KEY = 'pending_knowledge_base_id'
const PENDING_TOPIC_KEY = 'pending_topic_name'
const PENDING_COUNT_KEY = 'pending_question_count'
const PENDING_DRILL_ROUND_KEY = 'pending_drill_round'

export function setPendingSourceText(text: string) {
  Taro.setStorageSync(PENDING_TEXT_KEY, text)
}

export function setPendingQuizStart(opts: {
  source_text: string
  knowledge_base_id?: number
  topic_name?: string
  question_count?: number
  drill_round?: 'review'
}) {
  Taro.setStorageSync(PENDING_TEXT_KEY, opts.source_text)
  if (opts.knowledge_base_id != null) {
    Taro.setStorageSync(PENDING_KB_KEY, opts.knowledge_base_id)
  } else {
    try {
      Taro.removeStorageSync(PENDING_KB_KEY)
    } catch {
      /* ignore */
    }
  }
  if (opts.topic_name) {
    Taro.setStorageSync(PENDING_TOPIC_KEY, opts.topic_name)
  } else {
    try {
      Taro.removeStorageSync(PENDING_TOPIC_KEY)
    } catch {
      /* ignore */
    }
  }
  if (opts.question_count != null) {
    Taro.setStorageSync(PENDING_COUNT_KEY, opts.question_count)
  } else {
    try {
      Taro.removeStorageSync(PENDING_COUNT_KEY)
    } catch {
      /* ignore */
    }
  }
  if (opts.drill_round) {
    Taro.setStorageSync(PENDING_DRILL_ROUND_KEY, opts.drill_round)
  } else {
    try {
      Taro.removeStorageSync(PENDING_DRILL_ROUND_KEY)
    } catch {
      /* ignore */
    }
  }
}

export function takePendingQuizStart(): {
  source_text: string
  knowledge_base_id?: number
  topic_name?: string
  question_count?: number
  drill_round?: 'review'
} {
  try {
    const source_text = String(Taro.getStorageSync(PENDING_TEXT_KEY) || '')
    const kbRaw = Taro.getStorageSync(PENDING_KB_KEY)
    const topic_name = String(Taro.getStorageSync(PENDING_TOPIC_KEY) || '') || undefined
    const countRaw = Taro.getStorageSync(PENDING_COUNT_KEY)
    const roundRaw = String(Taro.getStorageSync(PENDING_DRILL_ROUND_KEY) || '')
    Taro.removeStorageSync(PENDING_TEXT_KEY)
    try {
      Taro.removeStorageSync(PENDING_KB_KEY)
    } catch {
      /* ignore */
    }
    try {
      Taro.removeStorageSync(PENDING_TOPIC_KEY)
    } catch {
      /* ignore */
    }
    try {
      Taro.removeStorageSync(PENDING_COUNT_KEY)
    } catch {
      /* ignore */
    }
    try {
      Taro.removeStorageSync(PENDING_DRILL_ROUND_KEY)
    } catch {
      /* ignore */
    }
    const knowledge_base_id =
      kbRaw === '' || kbRaw == null ? undefined : Number(kbRaw)
    const question_count =
      countRaw === '' || countRaw == null ? undefined : Number(countRaw)
    return {
      source_text,
      knowledge_base_id:
        knowledge_base_id != null && !Number.isNaN(knowledge_base_id)
          ? knowledge_base_id
          : undefined,
      topic_name,
      question_count:
        question_count != null && !Number.isNaN(question_count)
          ? question_count
          : undefined,
      drill_round: roundRaw === 'review' ? 'review' : undefined,
    }
  } catch {
    return { source_text: '' }
  }
}

/** @deprecated prefer takePendingQuizStart */
export function takePendingSourceText(): string {
  return takePendingQuizStart().source_text
}
