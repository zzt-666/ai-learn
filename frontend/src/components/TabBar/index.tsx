import { View, Text } from '@tarojs/components'
import Taro from '@tarojs/taro'
import './index.scss'

type TabId = 'home' | 'bank' | 'me'

const TABS: { id: TabId; label: string; path: string; glyph: string }[] = [
  { id: 'home', label: '开局', path: '/pages/home/index', glyph: '⌂' },
  { id: 'bank', label: '题目', path: '/pages/bank/index', glyph: '題' },
  { id: 'me', label: '我的', path: '/pages/me/index', glyph: '我' },
]

interface Props {
  active: TabId
}

export default function TabBar({ active }: Props) {
  const go = (path: string, id: TabId) => {
    if (id === active) return
    Taro.reLaunch({ url: path })
  }

  return (
    <View className='tabbar-dock'>
      <View className='tabbar'>
        {TABS.map((tab) => (
          <View
            key={tab.id}
            className={`tabbar-item ${tab.id === active ? 'active' : ''}`}
            onClick={() => go(tab.path, tab.id)}
          >
            <View className={`tab-icon tab-icon-${tab.id}`}>
              <Text className='tab-glyph'>{tab.glyph}</Text>
            </View>
            <Text className='tab-label'>{tab.label}</Text>
          </View>
        ))}
      </View>
    </View>
  )
}
