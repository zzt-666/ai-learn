import { useMemo, useState } from 'react'
import { View, Text, ScrollView } from '@tarojs/components'
import Taro, { useDidShow, useRouter } from '@tarojs/taro'
import Mascot from '../../components/Mascot'
import type { ReportPayload } from '../../types/quiz'
import type { HistoryDetail } from '../../types/user'
import { ApiError, fetchHistoryDetail, fetchHistoryReport, retryHistory } from '../../utils/api'
import { saveSession } from '../../utils/storage'
import type { QuizSession } from '../../types/quiz'
import '../../styles/ui.scss'
import './report.scss'

export default function HistoryReportPage() {
  const router = useRouter()
  const id = Number(router.params.id || 0)
  const [detail, setDetail] = useState<HistoryDetail | null>(null)
  const [report, setReport] = useState<ReportPayload | null>(null)
  const [error, setError] = useState('')

  const load = async () => {
    if (!id) {
      setError('无效的记录')
      return
    }
    try {
      const [d, r] = await Promise.all([fetchHistoryDetail(id), fetchHistoryReport(id)])
      setDetail(d)
      setReport(r)
      setError('')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '报告加载失败')
    }
  }

  useDidShow(() => {
    load()
  })

  const accuracyPct = useMemo(
    () => Math.round((report?.accuracy || 0) * 100),
    [report],
  )

  const onRetry = async () => {
    if (!detail) return
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
    }
  }

  if (error && !report) {
    return (
      <View className='page-shell'>
        <View className='page-body'>
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

  if (!report || !detail) {
    return <View className='page-shell' />
  }

  return (
    <View className='page-shell'>
      <ScrollView scrollY className='page-body immersive report-body'>
        <View className='row' style={{ alignItems: 'center' }}>
          <Mascot mood='happy' size='sm' />
          <View className='grow'>
            <Text className='panel-title' style={{ marginBottom: 0 }}>
              旧报告翻出来了
            </Text>
            <Text className='hint'>{detail.topic_name}</Text>
          </View>
        </View>

        <View className='score-summary'>
          <View className='acc-block'>
            <Text className='acc-num'>{accuracyPct}%</Text>
            <Text className='acc-label'>正确率</Text>
          </View>
          <View className='score-pair'>
            <View className='stat'>
              <Text className='stat-b'>{report.correct_count}</Text>
              <Text className='stat-s'>答对</Text>
            </View>
            <View className='stat'>
              <Text className='stat-b'>{report.wrong_count}</Text>
              <Text className='stat-s'>答错</Text>
            </View>
          </View>
        </View>

        <View className='comic-panel'>
          <Text className='panel-title'>薄弱点（当时）</Text>
          {report.weaknesses.map((w, i) => (
            <Text key={i} className='bullet'>
              · {w}
            </Text>
          ))}
        </View>

        <View className='comic-panel'>
          <Text className='panel-title'>错题回顾</Text>
          {report.wrong_review.length === 0 ? (
            <Text className='hint'>本局没有错题，漂亮！</Text>
          ) : (
            report.wrong_review.map((item) => (
              <View key={item.question_id} className='wrong-item'>
                <Text
                  className={`type-chip ${
                    item.type === 'multiple' ? 'multi' : item.type === 'boolean' ? 'bool' : ''
                  }`}
                >
                  {item.type === 'multiple' ? '多选' : item.type === 'boolean' ? '判断' : '单选'}
                </Text>
                <Text className='wrong-text'>
                  {item.stem}：{item.brief_reason}
                </Text>
              </View>
            ))
          )}
        </View>

        <View className='comic-panel'>
          <Text className='panel-title'>知识要点</Text>
          {report.summary_points.map((p, i) => (
            <Text key={i} className='bullet'>
              · {p}
            </Text>
          ))}
        </View>

        <View className='btn' onClick={onRetry}>
          重闯本主题
        </View>
        <View className='btn secondary' onClick={() => Taro.navigateBack()}>
          返回
        </View>
      </ScrollView>
    </View>
  )
}
