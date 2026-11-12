import { useMemo, useState } from 'react'
import { View, Text, ScrollView } from '@tarojs/components'
import Taro, { useDidShow, useRouter } from '@tarojs/taro'
import AccuracyRing from '../../components/AccuracyRing'
import Mascot from '../../components/Mascot'
import type { QuizSession, ReportPayload } from '../../types/quiz'
import type { HistoryDetail } from '../../types/user'
import { ApiError, fetchHistoryDetail, fetchHistoryReport, retryHistory } from '../../utils/api'
import { pickCheerTitle } from '../../utils/cheer'
import { saveSession } from '../../utils/storage'
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

  const openShare = () => {
    if (!detail || !report) return
    const session: QuizSession = {
      topic_name: detail.topic_name,
      source_text: '',
      questions: [],
      answers: [],
      current_index: 0,
      report,
      status: 'done',
      session_id: detail.id,
      exp_gained: detail.exp_gained,
      points_gained: detail.points_gained,
    }
    saveSession(session)
    Taro.navigateTo({ url: '/pages/share/index' })
  }

  if (error && !report) {
    return (
      <View className='page-shell'>
        <View className='page-body immersive'>
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
    <View className='page-shell report-shell'>
      <ScrollView scrollY className='report-scroll'>
        <View className='report-scroll-inner'>
          <View className='report-head'>
            <Mascot mood='happy' size='sm' />
            <View className='grow'>
              <Text className='report-cheer'>{pickCheerTitle(report.accuracy)}</Text>
              <Text className='report-topic'>{detail.topic_name}</Text>
            </View>
          </View>

          <View className='score-summary'>
            <AccuracyRing percent={accuracyPct} size={216} />
            <View className='score-pair'>
              <View className='stat ok'>
                <Text className='stat-b'>{report.correct_count}</Text>
                <Text className='stat-s'>答对</Text>
              </View>
              <View className='stat bad'>
                <Text className='stat-b'>{report.wrong_count}</Text>
                <Text className='stat-s'>答错</Text>
              </View>
            </View>
          </View>

          <View className='comic-panel report-card'>
            <Text className='report-section-title'>本局收获</Text>
            <View className='reward-row'>
              <Text className='reward-chip xp'>+{detail.exp_gained} EXP</Text>
              <Text className='reward-chip'>+{detail.points_gained} 积分</Text>
            </View>
            <Text className='report-settle-hint'>
              已按正确率结算 EXP / 积分，可在「我的」查看成长。
            </Text>
          </View>

          <View className='comic-panel report-card'>
            <Text className='report-section-title'>知识要点</Text>
            {report.summary_points.map((p, i) => (
              <Text key={i} className='bullet'>
                <Text className='bullet-dot'>·</Text> {p}
              </Text>
            ))}
          </View>

          <View className='comic-panel report-card'>
            <Text className='report-section-title'>错题回顾</Text>
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

          <View className='comic-panel report-card'>
            <Text className='report-section-title'>薄弱点</Text>
            {report.weaknesses.map((w, i) => (
              <Text key={i} className='bullet'>
                <Text className='bullet-dot'>·</Text> {w}
              </Text>
            ))}
          </View>
        </View>
      </ScrollView>

      <View className='report-footer'>
        <View className='report-footer-row'>
          <View className='btn sky' onClick={openShare}>
            生成海报并分享
          </View>
          <View className='btn' onClick={onRetry}>
            重闯本主题
          </View>
        </View>
      </View>
    </View>
  )
}
