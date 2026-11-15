import { useState } from 'react'
import { View, Text } from '@tarojs/components'
import Taro from '@tarojs/taro'
import {
  ApiError,
  createKnowledgeBase,
  uploadKnowledgeDocument,
} from '../../utils/api'
import { ensureLogin } from '../../utils/auth'
import '../../styles/ui.scss'
import './import.scss'

function stemFromFilename(filename: string) {
  const base = filename.trim()
  const idx = base.lastIndexOf('.')
  if (idx <= 0) return base || '未命名资料'
  return base.slice(0, idx) || base
}

export default function BankImportPage() {
  const [busy, setBusy] = useState(false)

  const onPickAndIngest = async () => {
    if (busy) return
    try {
      setBusy(true)
      await ensureLogin()
      const chosen = await Taro.chooseMessageFile({
        count: 1,
        type: 'file',
        extension: ['pdf', 'docx', 'md', 'markdown'],
      })
      const picked = chosen.tempFiles?.[0]
      if (!picked) return

      const name = stemFromFilename(picked.name)
      Taro.showLoading({ title: '上传中…', mask: true })
      const kb = await createKnowledgeBase({ name })
      await uploadKnowledgeDocument(kb.id, picked.path, picked.name)
      Taro.hideLoading()
      Taro.showToast({ title: '已上传，正在解析', icon: 'none' })
      Taro.redirectTo({ url: `/pages/bank/detail?id=${kb.id}` })
    } catch (err) {
      Taro.hideLoading()
      const msg =
        err instanceof ApiError
          ? err.message
          : typeof err === 'object' && err && 'errMsg' in err
            ? String((err as { errMsg?: string }).errMsg || '')
            : '导入失败'
      if (!/cancel|取消/i.test(msg)) {
        Taro.showToast({ title: msg.slice(0, 40) || '导入失败', icon: 'none' })
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <View className='page-shell'>
      <View className='page-body bank-import-body'>
        <View
          className={`upload-drop ${busy ? 'active' : ''}`}
          onClick={() => void onPickAndIngest()}
        >
          <View className='upload-glyph'>文</View>
          <Text className='upload-title'>
            {busy ? '上传中…' : '把 PDF / Word / MD 丢进来'}
          </Text>
          <Text className='upload-sub'>
            从微信聊天记录选择文件，上传后自动解析入库，主题名默认用文件名，可稍后修改
          </Text>
        </View>
      </View>
    </View>
  )
}
