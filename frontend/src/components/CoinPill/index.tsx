import { View, Text } from '@tarojs/components'
import './index.scss'

interface Props {
  value?: number | string
}

/** 仅 UI 占位：积分展示，无真实结算逻辑 */
export default function CoinPill({ value = 360 }: Props) {
  return (
    <View className='coin-pill'>
      <View className='coin-face'>
        <Text>分</Text>
      </View>
      <Text>{value}</Text>
    </View>
  )
}
