import { useState } from 'react'
import { View, Text } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import Mascot from '../../components/Mascot'
import type { HistoryItem } from '../../types/user'
import { ApiError, fetchHistory } from '../../utils/api'
import { accuracyPercent, formatFinishedAt } from '../../utils/format'
import '../../styles/ui.scss'
import './index.scss'

export default function HistoryPage() {
  const [items, setItems] = useState<HistoryItem[] | null>(null)
  const [error, setError] = useState('')

  const load = async () => {
    setError('')
    try {
      const list = await fetchHistory()
      setItems(list)
    } catch (err) {
      setItems([])
      setError(err instanceof ApiError ? err.message : '历史加载失败')
    }
  }

  useDidShow(() => {
    load()
  })

  return (
    <View className='page-shell'>
      <View className='page-body history-body immersive'>
        {items && items.length === 0 && !error ? (
          <View className='empty'>
            <Mascot mood='sweat' size='lg' />
            <Text className='empty-title'>这儿空空如也</Text>
            <Text className='hint empty-hint'>
              还没留下足迹。去粘一段材料，开第一局——报告会自动躺这儿。
            </Text>
            <View
              className='btn'
              style={{ maxWidth: '400rpx' }}
              onClick={() => Taro.reLaunch({ url: '/pages/home/index' })}
            >
              去开一局
            </View>
          </View>
        ) : (
          <>
            {error ? (
              <View className='comic-panel'>
                <Text className='hint warn'>{error}</Text>
                <View className='btn secondary' onClick={load}>
                  重新加载
                </View>
              </View>
            ) : null}

            {(items || []).map((item) => (
              <View
                key={item.id}
                className='list-item'
                onClick={() =>
                  Taro.navigateTo({ url: `/pages/history/report?id=${item.id}` })
                }
              >
                <Mascot mood='idle' size='tiny' />
                <View className='meta grow'>
                  <Text className='meta-title'>{item.topic_name}</Text>
                  <Text className='meta-sub'>
                    {formatFinishedAt(item.finished_at)} · 正确率：
                    {accuracyPercent(item.accuracy)}%
                  </Text>
                  <View className='history-reward-tags'>
                    <Text className='history-tag history-tag-xp'>
                      +{item.exp_gained} EXP
                    </Text>
                    <Text className='history-tag history-tag-pts'>
                      +{item.points_gained} 积分
                    </Text>
                  </View>
                </View>
                <Text className='badge'>已通关</Text>
              </View>
            ))}
          </>
        )}
      </View>
    </View>
  )
}
