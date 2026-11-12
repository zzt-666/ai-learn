import { View, Text } from '@tarojs/components'
import Taro from '@tarojs/taro'
import TabBar from '../../components/TabBar'
import '../../styles/ui.scss'
import './index.scss'

/** 仅 UI：题库页，无导入/再闯逻辑 */
export default function BankPage() {
  return (
    <View className='page-shell'>
      <View className='page-body bank-body'>
        <Text className='panel-title'>我的题库</Text>
        <Text className='hint'>存放导入与 AI 生成的题目，点开可再闯。</Text>

        <View className='list-item' onClick={() => Taro.showToast({ title: '即将上线', icon: 'none' })}>
          <View className='deco book' />
          <View className='meta'>
            <Text className='meta-title'>光合作用要点</Text>
            <Text className='meta-sub'>AI 生成 · 6 题 · 今天</Text>
          </View>
          <Text className='badge'>可闯</Text>
        </View>

        <View className='list-item' onClick={() => Taro.showToast({ title: '即将上线', icon: 'none' })}>
          <View className='deco bulb' />
          <View className='meta'>
            <Text className='meta-title'>民法总则速记</Text>
            <Text className='meta-sub'>AI 生成 · 10 题 · 昨天</Text>
          </View>
          <Text className='badge'>可闯</Text>
        </View>

        <View className='list-item' onClick={() => Taro.showToast({ title: '即将上线', icon: 'none' })}>
          <View className='deco pdf'>
            <Text>PDF</Text>
          </View>
          <View className='meta'>
            <Text className='meta-title'>期末复习导入包</Text>
            <Text className='meta-sub'>文档导入 · 18 题</Text>
          </View>
          <Text className='badge doing'>导入</Text>
        </View>

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
