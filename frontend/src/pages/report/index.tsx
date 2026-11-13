import { useEffect, useMemo, useRef, useState } from 'react'
import { View, Text, ScrollView } from '@tarojs/components'
import Taro, { useDidShow, useUnload } from '@tarojs/taro'
import AccuracyRing from '../../components/AccuracyRing'
import Mascot from '../../components/Mascot'
import type { QuizSession } from '../../types/quiz'
import { ApiError } from '../../utils/api'
import { pickCheerTitle } from '../../utils/cheer'
import { summarize } from '../../utils/grading'
import { ensureReportBuilt } from '../../utils/reportBuild'
import { clearSession, loadSession, saveSession } from '../../utils/storage'
import '../../styles/ui.scss'
import './index.scss'

type EnrichPhase = 'loading' | 'ready' | 'fail'

export default function ReportPage() {
  const [session, setSession] = useState<QuizSession | null>(null)
  const [enrichPhase, setEnrichPhase] = useState<EnrichPhase>('loading')
  const [enrichError, setEnrichError] = useState('')
  const [saving, setSaving] = useState(false)
  const leftRef = useRef(false)
  const tipOnLeaveRef = useRef(false)

  const syncFromStorage = () => {
    const s = loadSession()
    if (!s || !s.questions?.length || !s.answers?.length) {
      Taro.showToast({ title: '暂无报告', icon: 'none' })
      Taro.reLaunch({ url: '/pages/home/index' })
      return null
    }
    setSession(s)
    if (s.report) {
      setEnrichPhase('ready')
      tipOnLeaveRef.current = false
    } else {
      setEnrichPhase('loading')
      tipOnLeaveRef.current = true
    }
    return s
  }

  const runEnrich = async (s: QuizSession) => {
    setEnrichPhase('loading')
    setEnrichError('')
    tipOnLeaveRef.current = !s.report
    try {
      const next = await ensureReportBuilt(s)
      if (leftRef.current) return
      setSession(next)
      setEnrichPhase('ready')
      tipOnLeaveRef.current = false
    } catch (err) {
      if (leftRef.current) return
      const msg = err instanceof ApiError ? err.message : '报告生成失败，请重试'
      setEnrichError(msg)
      setEnrichPhase('fail')
      // Still leave tip if never got a report into storage.
      tipOnLeaveRef.current = !loadSession()?.report
    }
  }

  useDidShow(() => {
    leftRef.current = false
    const s = syncFromStorage()
    if (!s) return
    if (!s.report || s.pending_complete) {
      void runEnrich(s)
    }
  })

  useUnload(() => {
    leftRef.current = true
    if (tipOnLeaveRef.current) {
      Taro.showToast({
        title: '报告还在生成，可稍后在历史查看',
        icon: 'none',
        duration: 2500,
      })
    }
  })

  useEffect(() => {
    // Keep status as reporting until enriched.
    if (!session || session.report) return
    if (session.status !== 'reporting') {
      const next = { ...session, status: 'reporting' as const }
      saveSession(next)
      setSession(next)
    }
  }, [session])

  const stats = useMemo(() => {
    if (!session) return { correct_count: 0, wrong_count: 0, accuracy: 0 }
    return summarize(session.answers)
  }, [session])

  const accuracyPct = useMemo(
    () => Math.round(stats.accuracy * 100),
    [stats.accuracy],
  )

  if (!session) {
    return <View className='page-shell' />
  }

  const report = session.report
  const enrichReady = enrichPhase === 'ready' && !!report

  const again = () => {
    if (!enrichReady) return
    tipOnLeaveRef.current = false
    clearSession()
    Taro.reLaunch({ url: '/pages/home/index' })
  }

  const openShare = () => {
    if (!enrichReady) return
    tipOnLeaveRef.current = false
    Taro.navigateTo({ url: '/pages/share/index' })
  }

  const retryComplete = async () => {
    if (!session.report || saving) return
    setSaving(true)
    try {
      const next = await ensureReportBuilt(session)
      setSession(next)
      Taro.showToast({ title: '记录已保存', icon: 'success' })
    } catch (err) {
      Taro.showToast({
        title: err instanceof ApiError ? err.message : '保存失败，请重试',
        icon: 'none',
      })
    } finally {
      setSaving(false)
    }
  }

  const expText =
    session.exp_gained != null ? `+${session.exp_gained} EXP` : '结算中…'
  const pointsText =
    session.points_gained != null ? `+${session.points_gained} 积分` : '—'

  return (
    <View className='page-shell report-shell'>
      <ScrollView scrollY className='report-scroll'>
        <View className='report-scroll-inner'>
          <View className='report-head'>
            <Mascot mood='cheer' size='sm' />
            <View className='grow'>
              <Text className='report-cheer'>{pickCheerTitle(stats.accuracy)}</Text>
              <Text className='report-topic'>{session.topic_name}</Text>
            </View>
            <View className='trophy'>🏆</View>
          </View>

          <View className='score-summary'>
            <AccuracyRing percent={accuracyPct} size={216} />
            <View className='score-pair'>
              <View className='stat ok'>
                <Text className='stat-b'>{stats.correct_count}</Text>
                <Text className='stat-s'>答对</Text>
              </View>
              <View className='stat bad'>
                <Text className='stat-b'>{stats.wrong_count}</Text>
                <Text className='stat-s'>答错</Text>
              </View>
            </View>
          </View>

          {!enrichReady ? (
            <View className='comic-panel report-card report-enrich-wait'>
              {enrichPhase === 'fail' ? (
                <>
                  <Text className='report-section-title'>总结还没写好</Text>
                  <Text className='report-settle-hint warn'>{enrichError}</Text>
                  <View
                    className='btn'
                    style={{ marginTop: '24rpx' }}
                    onClick={() => void runEnrich(session)}
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
                  <Text className='reward-chip xp'>{expText}</Text>
                  <Text className='reward-chip'>{pointsText}</Text>
                </View>
                {session.pending_complete ? (
                  <>
                    <Text className='report-settle-hint warn'>
                      记录还没存上云，积分可能未到账。点下面重试一下。
                    </Text>
                    <View
                      className={`btn secondary ${saving ? 'disabled' : ''}`}
                      style={{ marginTop: '24rpx' }}
                      onClick={retryComplete}
                    >
                      {saving ? '保存中…' : '重试保存记录'}
                    </View>
                  </>
                ) : (
                  <Text className='report-settle-hint'>
                    已按正确率结算 EXP / 积分，可在「我的」查看成长。
                  </Text>
                )}
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
                {report.weaknesses.map((w, i) => (
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
            onClick={again}
          >
            再来一局
          </View>
        </View>
      </View>
    </View>
  )
}
