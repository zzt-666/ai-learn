import { useState } from 'react'
import { View, Text } from '@tarojs/components'
import Taro, { useDidShow, useRouter } from '@tarojs/taro'
import type { HistoryDetail } from '../../types/user'
import { ApiError, fetchHistoryDetail, retryHistory } from '../../utils/api'
import { accuracyPercent, formatFinishedAt } from '../../utils/format'
import { saveSession } from '../../utils/storage'
import type { QuizSession } from '../../types/quiz'
import '../../styles/ui.scss'
import './detail.scss'

export default function HistoryDetailPage() {
  const router = useRouter()
  const id = Number(router.params.id || 0)
  const [detail, setDetail] = useState<HistoryDetail | null>(null)
  const [error, setError] = useState('')
  const [retrying, setRetrying] = useState(false)

  const load = async () => {
    if (!id) {
      setError('无效的记录')
      return
    }
    try {
      const data = await fetchHistoryDetail(id)
      setDetail(data)
      setError('')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '加载失败')
    }
  }

  useDidShow(() => {
    load()
  })

  const onRetry = async () => {
    if (!detail || retrying) return
    setRetrying(true)
    try {
      const payload = await retryHistory(detail.id)
      const session: QuizSession = {
        topic_name: payload.topic_name,
        source_text: payload.source_text,
        questions: payload.questions,
        answers: [],
        current_index: 0,
        report: null,
        status: 'answering',
        source_session_id: payload.source_session_id,
      }
      saveSession(session)
      Taro.redirectTo({ url: '/pages/quiz/index' })
    } catch (err) {
      Taro.showToast({
        title: err instanceof ApiError ? err.message : '重闯失败',
        icon: 'none',
      })
    } finally {
      setRetrying(false)
    }
  }

  if (error && !detail) {
    return (
      <View className='page-shell'>
        <View className='page-body'>
          <View className='btn ghost' onClick={() => Taro.navigateBack()}>
            ← 历史
          </View>
          <View className='comic-panel'>
            <Text className='hint warn'>{error}</Text>
            <View className='btn secondary' onClick={load}>
              重试
            </View>
          </View>
        </View>
      </View>
    )
  }

  if (!detail) {
    return <View className='page-shell' />
  }

  const pct = accuracyPercent(detail.accuracy)

  return (
    <View className='page-shell'>
      <View className='page-body detail-body'>
        <View className='btn ghost' onClick={() => Taro.navigateBack()}>
          ← 历史
        </View>

        <View className='comic-panel'>
          <Text className='panel-title' style={{ marginBottom: 0 }}>
            {detail.topic_name}
          </Text>
          <Text className='hint' style={{ marginTop: '12rpx' }}>
            {formatFinishedAt(detail.finished_at)} 通关 · 单选/多选/判断混合
          </Text>
          <View className='score-summary compact'>
            <View className='acc-block'>
              <Text className='acc-num'>{pct}%</Text>
              <Text className='acc-label'>正确率</Text>
            </View>
            <View className='score-pair'>
              <View className='stat'>
                <Text className='stat-b'>+{detail.exp_gained}</Text>
                <Text className='stat-s'>EXP</Text>
              </View>
              <View className='stat'>
                <Text className='stat-b'>+{detail.points_gained}</Text>
                <Text className='stat-s'>积分</Text>
              </View>
            </View>
          </View>
        </View>

        <View
          className='btn'
          onClick={() =>
            Taro.navigateTo({ url: `/pages/history/report?id=${detail.id}` })
          }
        >
          看复盘报告
        </View>
        <View className={`btn secondary ${retrying ? 'disabled' : ''}`} onClick={onRetry}>
          {retrying ? '准备重闯…' : '重闯这一局'}
        </View>
        <View className='comic-bubble'>
          重闯会重新答题，报告另记一笔——不怕丢脸，丢脸长记性。
        </View>
      </View>
    </View>
  )
}
