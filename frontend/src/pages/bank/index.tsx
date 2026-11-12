import { View, Text } from '@tarojs/components'
import Taro from '@tarojs/taro'
import TabBar from '../../components/TabBar'
import '../../styles/ui.scss'
import './index.scss'

const PLACEHOLDERS = [
  { title: '光合作用要点', sub: 'AI 生成 · 6 题 · 今天', badge: '可闯', doing: false },
  { title: '民法总则速记', sub: 'AI 生成 · 10 题 · 昨天', badge: '可闯', doing: false },
  { title: '期末复习导入包', sub: '文档导入 · 18 题', badge: '导入', doing: true },
]

/** 仅 UI：题库页，无导入/再闯逻辑 */
export default function BankPage() {
  return (
    <View className='page-shell'>
      <View className='page-body bank-body'>
        <Text className='panel-title'>我的题库</Text>
        <Text className='hint'>存放导入与 AI 生成的题目，点开可再闯。</Text>

        {PLACEHOLDERS.map((item) => (
          <View
            key={item.title}
            className='list-item'
            onClick={() => Taro.showToast({ title: '即将上线', icon: 'none' })}
          >
            <View className={`deco tone-${item.title.charCodeAt(0) % 3}`}>
              <Text className='deco-char'>{item.title.slice(0, 1)}</Text>
            </View>
            <View className='meta'>
              <Text className='meta-title'>{item.title}</Text>
              <Text className='meta-sub'>{item.sub}</Text>
            </View>
            <Text className={`badge ${item.doing ? 'doing' : ''}`}>{item.badge}</Text>
          </View>
        ))}

        <View
          className='btn secondary mt-auto'
          onClick={() => Taro.showToast({ title: '即将上线', icon: 'none' })}
        >
          导入题目 / 文档
        </View>
      </View>
      <TabBar active='bank' />
    </View>
  )
}
