import { View, Text } from '@tarojs/components'
import Taro from '@tarojs/taro'
import Mascot from '../../components/Mascot'
import TabBar from '../../components/TabBar'
import '../../styles/ui.scss'
import './index.scss'

/** 仅 UI：「我的」页，无登录与真实积分逻辑 */
export default function MePage() {
  return (
    <View className='page-shell'>
      <View className='page-body me-body'>
        <View className='me-hero comic-panel'>
          <Mascot mood='cheer' size='sm' />
          <View className='grow'>
            <Text className='panel-title'>阿衰同学</Text>
            <Text className='hint'>游客模式 · 本期无登录</Text>
            <View className='pill-row'>
              <Text className='pill'>Lv.5</Text>
              <Text className='pill xp'>EXP 1280</Text>
              <Text className='pill coin'>积分 360</Text>
            </View>
          </View>
        </View>

        <View className='list-item' onClick={() => Taro.showToast({ title: '示意入口，本期不接历史', icon: 'none' })}>
          <View className='meta'>
            <Text className='meta-title'>学习历史</Text>
            <Text className='meta-sub'>报告回看 / 重闯 · 后置</Text>
          </View>
        </View>
        <View className='list-item' onClick={() => Taro.showToast({ title: '示意入口，本期不接', icon: 'none' })}>
          <View className='meta'>
            <Text className='meta-title'>积分怎么用？（示意）</Text>
            <Text className='meta-sub'>换题量加成 / 皮肤贴纸 · 商业化后置</Text>
          </View>
        </View>
      </View>
      <TabBar active='me' />
    </View>
  )
}
