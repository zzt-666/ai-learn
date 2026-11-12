import { useMemo, useState } from 'react'
import { View, Text, ScrollView } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import AccuracyRing from '../../components/AccuracyRing'
import Mascot from '../../components/Mascot'
import type { QuizSession } from '../../types/quiz'
import { ApiError, completeSession } from '../../utils/api'
import { pickCheerTitle } from '../../utils/cheer'
import { clearSession, loadSession, saveSession } from '../../utils/storage'
import '../../styles/ui.scss'
import './index.scss'

export default function ReportPage() {
  const [session, setSession] = useState<QuizSession | null>(null)
  const [saving, setSaving] = useState(false)

  useDidShow(() => {
    const s = loadSession()
    if (!s?.report) {
      Taro.showToast({ title: '暂无报告', icon: 'none' })
      Taro.reLaunch({ url: '/pages/home/index' })
      return
    }
    setSession(s)
  })

  const report = session?.report
  const accuracyPct = useMemo(
    () => Math.round((report?.accuracy || 0) * 100),
    [report],
  )

  if (!session || !report) {
    return <View className='page-shell' />
  }

  const again = () => {
    clearSession()
    Taro.reLaunch({ url: '/pages/home/index' })
  }

  const retryComplete = async () => {
    if (!session.report || saving) return
    setSaving(true)
    try {
      const completed = await completeSession({
        topic_name: session.topic_name,
        source_text: session.source_text,
        questions: session.questions,
        answers: session.answers,
        report: session.report,
        source_session_id: session.source_session_id ?? null,
      })
      const next = {
        ...session,
        session_id: completed.session_id,
        exp_gained: completed.exp_gained,
        points_gained: completed.points_gained,
        pending_complete: false,
      }
      saveSession(next)
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
              <Text className='report-cheer'>{pickCheerTitle(report.accuracy)}</Text>
              <Text className='report-topic'>{session.topic_name}</Text>
            </View>
            <View className='trophy'>🏆</View>
          </View>

          <View className='score-summary'>
            <AccuracyRing percent={accuracyPct} />
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
          <View className='btn sky' onClick={() => Taro.navigateTo({ url: '/pages/share/index' })}>
            生成海报并分享
          </View>
          <View className='btn' onClick={again}>
            再来一局
          </View>
        </View>
      </View>
    </View>
  )
}
