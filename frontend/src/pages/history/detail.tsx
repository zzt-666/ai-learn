import { useEffect } from 'react'
import { View } from '@tarojs/components'
import Taro, { useRouter } from '@tarojs/taro'
import '../../styles/ui.scss'
import './detail.scss'

/** 兼容旧入口：主题详情已合并进历史报告页 */
export default function HistoryDetailRedirect() {
  const router = useRouter()
  const id = router.params.id || ''

  useEffect(() => {
    if (!id) {
      Taro.redirectTo({ url: '/pages/history/index' })
      return
    }
    Taro.redirectTo({ url: `/pages/history/report?id=${id}` })
  }, [id])

  return <View className='page-shell' />
}
