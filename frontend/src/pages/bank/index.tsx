import { useState } from 'react'
import { View, Text } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import TabBar from '../../components/TabBar'
import {
  ApiError,
  fetchKnowledgeBases,
  type KnowledgeBaseItem,
} from '../../utils/api'
import { ensureLogin } from '../../utils/auth'
import '../../styles/ui.scss'
import './index.scss'

export default function BankPage() {
  const [list, setList] = useState<KnowledgeBaseItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const refresh = async () => {
    setLoading(true)
    setError('')
    try {
      await ensureLogin()
      const rows = await fetchKnowledgeBases()
      setList(rows)
    } catch (err) {
      setList([])
      setError(err instanceof ApiError ? err.message : '加载失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  useDidShow(() => {
    refresh()
  })

  const goImport = async () => {
    try {
      await ensureLogin()
      Taro.navigateTo({ url: '/pages/bank/import' })
    } catch (err) {
      Taro.showToast({
        title: err instanceof ApiError ? err.message : '请先登录',
        icon: 'none',
      })
    }
  }

  return (
    <View className='page-shell'>
      <View className='page-body bank-body'>
        <Text className='panel-title'>我的知识库</Text>

        {error ? <Text className='hint warn'>{error}</Text> : null}
        {loading && !list.length ? <Text className='hint'>加载中…</Text> : null}

        {!loading && !list.length && !error ? (
          <View className='comic-panel'>
            <Text className='panel-title'>还没有文档</Text>
            <Text className='hint'>点下方导入一份 pdf / docx / md 即可开局。</Text>
          </View>
        ) : null}

        {list.map((item) => (
          <View
            key={item.id}
            className='list-item'
            onClick={() =>
              Taro.navigateTo({ url: `/pages/bank/detail?id=${item.id}` })
            }
          >
            <View className={`deco tone-${item.id % 3}`}>
              <Text className='deco-char'>{item.name.slice(0, 1)}</Text>
            </View>
            <View className='meta'>
              <Text className='meta-title'>{item.name}</Text>
              <Text className='meta-sub'>
                文档 {item.document_count} · 就绪 {item.ready_document_count}
                {item.mode === 'drill' && item.active_question_count
                  ? ` · ${item.active_question_count} 题`
                  : ''}
                {!item.ready_document_count ? ' · 待上传' : ''}
              </Text>
            </View>
            <Text
              className={`badge mode-${
                item.mode === 'drill'
                  ? 'drill'
                  : item.mode === 'master'
                    ? 'master'
                    : 'unset'
              }`}
            >
              {item.mode === 'drill'
                ? '刷题'
                : item.mode === 'master'
                  ? '学透'
                  : '未确认'}
            </Text>
          </View>
        ))}

        <View className='import-row'>
          <View className='btn' onClick={() => void goImport()}>
            导入文档
          </View>
        </View>
      </View>
      <TabBar active='bank' />
    </View>
  )
}
