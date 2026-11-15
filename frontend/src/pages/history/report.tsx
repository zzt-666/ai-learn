import { useEffect, useMemo, useRef, useState } from 'react'
import { View, Text, ScrollView } from '@tarojs/components'
import Taro, { useDidShow, useRouter } from '@tarojs/taro'
import AccuracyRing from '../../components/AccuracyRing'
import Mascot from '../../components/Mascot'
import type { QuizSession, ReportPayload } from '../../types/quiz'
import type { HistoryDetail } from '../../types/user'
import { ApiError, fetchHistoryDetail, fetchHistoryReport } from '../../utils/api'
import { pickCheerTitle } from '../../utils/cheer'
import { startRetryFromHistory } from '../../utils/resumeSession'
import { saveSession } from '../../utils/storage'
import '../../styles/ui.scss'
import './report.scss'

const POLL_MS = 2000

export default function HistoryReportPage() {
  const router = useRouter()
  const id = Number(router.params.id || 0)
  const [detail, setDetail] = useState<HistoryDetail | null>(null)
  const [report, setReport] = useState<ReportPayload | null>(null)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopPoll = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }

  const startPoll = () => {
    if (pollRef.current) return
    pollRef.current = setInterval(() => {
      void loadReportOnly()
    }, POLL_MS)
  }

  const loadReportOnly = async () => {
    if (!id) return
    try {
      const r = await fetchHistoryReport(id)
      if (r.status === 'ready' && r.report) {
        setReport(r.report)
        setPending(false)
        setError('')
        stopPoll()
        return
      }
      setPending(true)
      setReport(null)
      setError('')
      startPoll()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '报告加载失败')
      setPending(false)
    }
  }

  const load = async () => {
    if (!id) {
      setError('无效的记录')
      return
    }
    try {
      const [d, r] = await Promise.all([
        fetchHistoryDetail(id),
        fetchHistoryReport(id),
      ])
      setDetail(d)
      if (r.status === 'ready' && r.report) {
        setReport(r.report)
        setPending(false)
        stopPoll()
      } else {
        setReport(null)
        setPending(true)
        startPoll()
      }
      setError('')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '报告加载失败')
      setPending(false)
    }
  }

  useDidShow(() => {
    load()
  })

  useEffect(() => () => stopPoll(), [])

  const accuracy = report?.accuracy ?? detail?.accuracy ?? 0
  const correctCount = report?.correct_count ?? detail?.correct_count ?? 0
  const wrongCount = report?.wrong_count ?? detail?.wrong_count ?? 0
  const accuracyPct = useMemo(() => Math.round(accuracy * 100), [accuracy])
  const enrichReady = !!report && !pending

  const onRetry = async () => {
    if (!detail || !enrichReady) return
    try {
      await startRetryFromHistory(detail.id)
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

  if (error && !detail) {
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

  if (!detail) {
    return <View className='page-shell' />
  }

  return (
    <View className='page-shell report-shell'>
      <ScrollView scrollY className='report-scroll'>
        <View className='report-scroll-inner'>
          <View className='report-head'>
            <Mascot mood='cheer' size='sm' />
            <View className='grow'>
              <Text className='report-cheer'>{pickCheerTitle(accuracy)}</Text>
              <Text className='report-topic'>{detail.topic_name}</Text>
            </View>
            <View className='trophy'>🏆</View>
          </View>

          <View className='score-summary'>
            <AccuracyRing percent={accuracyPct} size={216} />
            <View className='score-pair'>
              <View className='stat ok'>
                <Text className='stat-b'>{correctCount}</Text>
                <Text className='stat-s'>答对</Text>
              </View>
              <View className='stat bad'>
                <Text className='stat-b'>{wrongCount}</Text>
                <Text className='stat-s'>答错</Text>
              </View>
            </View>
          </View>

          {!enrichReady ? (
            <View className='comic-panel report-card report-enrich-wait'>
              {error ? (
                <>
                  <Text className='report-section-title'>总结还没写好</Text>
                  <Text className='report-settle-hint warn'>{error}</Text>
                  <View
                    className='btn'
                    style={{ marginTop: '24rpx' }}
                    onClick={() => void loadReportOnly()}
                  >
                    再试一次
                  </View>
                </>
              ) : (
                <>
                  <View className='report-enrich-spinner' />
                  <Text className='report-section-title'>AI 正在生成总结…</Text>
                  <Text className='report-settle-hint'>
                    本局收获与知识要点写好后会一起出现，稍等一下。
                  </Text>
                </>
              )}
            </View>
          ) : (
            <>
              <View className='comic-panel report-card'>
                <Text className='report-section-title'>本局收获</Text>
                <View className='reward-row'>
                  <Text className='reward-chip xp'>+{detail.exp_gained} EXP</Text>
                  <Text className='reward-chip'>+{detail.points_gained} 积分</Text>
                </View>
                <Text className='report-settle-hint'>
                  已按答题结算 EXP / 积分（与局内一致），可在「我的」查看成长。
                </Text>
              </View>

              <View className='comic-panel report-card'>
                <Text className='report-section-title'>知识要点</Text>
                {report!.summary_points.map((p, i) => (
                  <Text key={i} className='bullet'>
                    <Text className='bullet-dot'>·</Text> {p}
                  </Text>
                ))}
              </View>

              <View className='comic-panel report-card'>
                <Text className='report-section-title'>错题回顾</Text>
                {report!.wrong_review.length === 0 ? (
                  <Text className='hint'>本局没有错题，漂亮！</Text>
                ) : (
                  report!.wrong_review.map((item) => (
                    <View key={item.question_id} className='wrong-item'>
                      <Text
                        className={`type-chip ${
                          item.type === 'multiple'
                            ? 'multi'
                            : item.type === 'boolean'
                              ? 'bool'
                              : ''
                        }`}
                      >
                        {item.type === 'multiple'
                          ? '多选'
                          : item.type === 'boolean'
                            ? '判断'
                            : '单选'}
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
                {report!.weaknesses.map((w, i) => (
                  <Text key={i} className='bullet'>
                    <Text className='bullet-dot'>·</Text> {w}
                  </Text>
                ))}
              </View>
            </>
          )}
        </View>
      </ScrollView>

      <View className='report-footer'>
        <View className='report-footer-row'>
          <View
            className={`btn sky ${enrichReady ? '' : 'disabled'}`}
            onClick={openShare}
          >
            生成海报并分享
          </View>
          <View
            className={`btn ${enrichReady ? '' : 'disabled'}`}
            onClick={onRetry}
          >
            重闯本主题
          </View>
        </View>
      </View>
    </View>
  )
}
