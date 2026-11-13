import { View, Text } from '@tarojs/components'
import Mascot from '../Mascot'
import '../../styles/ui.scss'
import './index.scss'

type Mood = 'idle' | 'happy' | 'sweat' | 'think' | 'cheer'

interface ConfirmModalProps {
  open: boolean
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  mood?: Mood
  onConfirm: () => void
  onCancel: () => void
}

export default function ConfirmModal({
  open,
  title,
  message,
  confirmText = '确定',
  cancelText = '再想想',
  mood = 'sweat',
  onConfirm,
  onCancel,
}: ConfirmModalProps) {
  if (!open) return null

  return (
    <View className='cfm-mask' catchMove onClick={onCancel}>
      <View
        className='cfm-card'
        onClick={(e) => {
          e.stopPropagation()
        }}
      >
        <Mascot mood={mood} size='md' />
        <Text className='cfm-title'>{title}</Text>
        <Text className='cfm-message'>{message}</Text>
        <View className='cfm-actions'>
          <View className='btn secondary cfm-btn' onClick={onCancel}>
            {cancelText}
          </View>
          <View className='btn cfm-btn' onClick={onConfirm}>
            {confirmText}
          </View>
        </View>
      </View>
    </View>
  )
}
