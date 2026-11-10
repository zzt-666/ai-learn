import { useState } from 'react'
import { View, Text, Textarea } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import CoinPill from '../../components/CoinPill'
import Mascot from '../../components/Mascot'
import TabBar from '../../components/TabBar'
import { setPendingSourceText } from '../../utils/pending'
import { hasSeenGuide, markGuideSeen } from '../../utils/storage'
import '../../styles/ui.scss'
import './index.scss'

export default function HomePage() {
  const [showGuide, setShowGuide] = useState(false)
  const [sourceText, setSourceText] = useState('')
  const [emptyWarn, setEmptyWarn] = useState(false)

  useDidShow(() => {
    setShowGuide(!hasSeenGuide())
  })

  const dismissGuide = () => {
    markGuideSeen()
    setShowGuide(false)
  }

  const startQuiz = () => {
    const text = sourceText.trim()
    if (!text) {
      setEmptyWarn(true)
      return
    }
    setEmptyWarn(false)
    setPendingSourceText(text)
    Taro.navigateTo({ url: '/pages/generate/index' })
  }

  if (showGuide) {
    return (
      <View className='page-shell guide-page'>
        <Mascot mood='cheer' size='lg' />
        <Text className='guide-title'>衰衰闯关</Text>
        <Text className='guide-sub'>粘一段 → 开一局 → 边答边学</Text>
        <View className='comic-bubble guide-bubble'>
          哟，别光「看过」就完事。把笔记砸给我，我给你整套闯关题——答完还有复盘报告，兄弟罩你。
        </View>
        <View className='btn guide-btn' onClick={dismissGuide}>
          开整！去粘贴 →
        </View>
        <Text className='hint'>约 1 分钟搞懂怎么玩</Text>
      </View>
    )
  }

  return (
    <View className='page-shell'>
      <View className='page-body home-body'>
        <View className='home-head'>
          <View className='hello-row'>
            <View className='brand-mark' />
            <Text className='hello-inline'>你好呀，阿衰同学</Text>
          </View>
          <CoinPill value={360} />
        </View>

        <View className='home-title-row'>
          <Text className='home-title'>今天想闯哪一关？</Text>
          <Mascot mood='idle' size='sm' />
        </View>

        <View className='stack'>
          <Text className='field-label'>粘贴学习材料</Text>
          <Textarea
            className={`textarea ${emptyWarn ? 'error' : ''}`}
            placeholder='粘贴一句话 / 一段笔记 / 长文本…主题名由 AI 自动生成'
            maxlength={8000}
            value={sourceText}
            onInput={(e) => {
              setSourceText(e.detail.value)
              if (e.detail.value.trim()) setEmptyWarn(false)
            }}
            autoHeight
          />
          {emptyWarn ? (
            <Text className='hint warn'>先贴点东西再开局——空着手我变不出题来。</Text>
          ) : null}
        </View>

        <View
          className={`btn ${sourceText.trim() ? '' : 'disabled'}`}
          onClick={startQuiz}
        >
          开始闯关！
        </View>
        <Text className='hint'>材料优先出题 · 主题名 AI 自动起，不用你填</Text>

        <Text className='section-label'>直接开闯</Text>
        <View className='quick-picks'>
          <View className='quick-pick' onClick={() => Taro.showToast({ title: '示意入口，本期不接逻辑', icon: 'none' })}>
            <Text className='qp-title'>光合作用要点</Text>
            <Text className='qp-sub'>题库 · 6 题 · 点此开闯</Text>
          </View>
          <View className='quick-pick' onClick={() => Taro.showToast({ title: '示意入口，本期不接逻辑', icon: 'none' })}>
            <Text className='qp-title'>民法总则速记</Text>
            <Text className='qp-sub'>题库 · 10 题 · 点此开闯</Text>
          </View>
        </View>

        <Text className='section-label'>未完成的闯关</Text>
        <View className='unfinished'>
          <View className='unfinished-item' onClick={() => Taro.showToast({ title: '示意卡片，本期不接续玩', icon: 'none' })}>
            <View className='ico'>
              <Mascot mood='think' size='tiny' />
            </View>
            <View className='meta'>
              <Text className='meta-title'>产品需求评审</Text>
              <Text className='meta-sub'>8 题 · 进行中</Text>
            </View>
            <View className='ring-text'>60%</View>
          </View>
          <View className='unfinished-item' onClick={() => Taro.showToast({ title: '示意卡片，本期不接续玩', icon: 'none' })}>
            <View className='ico bulb'>
              <Text>💡</Text>
            </View>
            <View className='meta'>
              <Text className='meta-title'>民法总则速记</Text>
              <Text className='meta-sub'>10 题 · 进行中</Text>
            </View>
            <View className='ring-text'>40%</View>
          </View>
        </View>
      </View>
      <TabBar active='home' />
    </View>
  )
}
