import { View, Text } from '@tarojs/components'
import './index.scss'

interface Props {
  percent: number
  size?: number
}

/** 圆形正确率进度：percent 0~100 */
export default function AccuracyRing({ percent, size = 176 }: Props) {
  const p = Math.max(0, Math.min(100, percent))
  const r = 34
  const c = 2 * Math.PI * r
  const offset = c * (1 - p / 100)

  return (
    <View className='acc-ring-wrap' style={{ width: `${size}rpx`, height: `${size}rpx` }}>
      <View
        className='acc-ring-svg'
        style={{
          backgroundImage: `url("data:image/svg+xml,${encodeURIComponent(
            `<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 88 88'><circle cx='44' cy='44' r='34' fill='none' stroke='#ffe2c4' stroke-width='8'/><circle cx='44' cy='44' r='34' fill='none' stroke='#ff9f3c' stroke-width='8' stroke-linecap='round' transform='rotate(-90 44 44)' stroke-dasharray='${c}' stroke-dashoffset='${offset}'/></svg>`,
          )}")`,
        }}
      />
      <View className='acc-ring-center'>
        <Text className='acc-num'>{p}%</Text>
        <Text className='acc-label'>正确率</Text>
      </View>
    </View>
  )
}
