import { useMemo, useState } from 'react'
import { View, Text, ScrollView } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import Mascot from '../../components/Mascot'
import type { QuizSession } from '../../types/quiz'
import { clearSession, loadSession } from '../../utils/storage'
import '../../styles/ui.scss'
import './index.scss'

export default function ReportPage() {
  const [session, setSession] = useState<QuizSession | null>(null)

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

  return (
    <View className='page-shell'>
      <ScrollView scrollY className='page-body immersive report-body'>
        <View className='row' style={{ alignItems: 'center' }}>
          <Mascot mood='cheer' size='sm' />
          <View className='grow'>
            <Text className='panel-title' style={{ marginBottom: 0 }}>
              通关！这局够味
            </Text>
            <Text className='hint'>{session.topic_name}</Text>
          </View>
          <View className='trophy'>🏆</View>
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
          <Text className='panel-title'>本局收获</Text>
          <View className='reward-row'>
            <Text className='reward-chip xp'>+95 EXP</Text>
            <Text className='reward-chip'>+28 积分</Text>
          </View>
          <Text className='hint' style={{ marginTop: '16rpx' }}>
            答对多、连续答对有小加成。（示意展示）
          </Text>
        </View>

        <View className='comic-panel'>
          <Text className='panel-title'>知识要点</Text>
          {report.summary_points.map((p, i) => (
            <Text key={i} className='bullet'>
              · {p}
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
          <Text className='panel-title'>薄弱点</Text>
          {report.weaknesses.map((w, i) => (
            <Text key={i} className='bullet'>
              · {w}
            </Text>
          ))}
        </View>

        <View
          className='btn sky'
          onClick={() => Taro.navigateTo({ url: '/pages/share/index' })}
        >
          生成海报并分享
        </View>
        <View className='btn' onClick={again}>
          再来一局
        </View>
        <View className='btn secondary' onClick={again}>
          回首页改材料
        </View>
      </ScrollView>
    </View>
  )
}
