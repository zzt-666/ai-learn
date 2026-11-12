import { useMemo, useState } from 'react'
import { View, Text, ScrollView } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import AccuracyRing from '../../components/AccuracyRing'
import Mascot from '../../components/Mascot'
import type { QuizSession } from '../../types/quiz'
import { loadSession } from '../../utils/storage'
import '../../styles/ui.scss'
import './index.scss'

/** 仅 UI：海报预览 + 占位按钮，不接微信分享/存相册真能力 */
export default function SharePage() {
  const [session, setSession] = useState<QuizSession | null>(null)

  useDidShow(() => {
    const s = loadSession()
    if (!s?.report) {
      Taro.navigateBack()
      return
    }
    setSession(s)
  })

  const report = session?.report
  const accuracyPct = useMemo(
    () => Math.round((report?.accuracy || 0) * 100),
    [report],
  )

  if (!session || !report) return <View className='page-shell' />

  return (
    <View className='page-shell share-shell'>
      <ScrollView scrollY className='page-body immersive share-body'>
        <View className='share-poster'>
          <View className='poster-brand'>
            <Mascot mood='cheer' size='tiny' />
            <View>
              <Text className='brand-name'>衰衰闯关</Text>
              <Text className='hint'>通关海报</Text>
            </View>
          </View>
          <Text className='poster-title'>我通关了「{session.topic_name}」</Text>
          <View className='score-summary compact'>
            <AccuracyRing percent={accuracyPct} size={160} />
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
          <View className='reward-row'>
            <Text className='reward-chip xp'>+95 EXP</Text>
            <Text className='reward-chip'>+28 积分</Text>
          </View>
          <Text className='hint'>
            要点：{(report.summary_points || []).slice(0, 3).join(' · ') || '本局要点见报告'}
          </Text>
          <View className='poster-foot'>
            <View className='qr-box'>
              <Text className='qr-text'>扫码打开</Text>
            </View>
            <View className='poster-cta'>
              <Text className='cta-title'>扫码打开小程序</Text>
              <Text className='cta-desc'>好友扫一扫即可进入同一主题闯关，来比一比？</Text>
            </View>
          </View>
        </View>

        <View className='share-actions'>
          <View
            className='btn'
            onClick={() => Taro.showToast({ title: '示意按钮，本期不接微信分享', icon: 'none' })}
          >
            分享给微信好友
          </View>
          <View
            className='btn secondary'
            onClick={() => Taro.showToast({ title: '示意按钮，本期不接存相册', icon: 'none' })}
          >
            保存海报到相册
          </View>
        </View>
      </ScrollView>
    </View>
  )
}
