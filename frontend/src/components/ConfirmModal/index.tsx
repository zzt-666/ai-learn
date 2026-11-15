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
  /** Optional third action (e.g. reset progress). */
  extraText?: string
  mood?: Mood
  onConfirm: () => void
  onCancel: () => void
  onExtra?: () => void
}

export default function ConfirmModal({
  open,
  title,
  message,
  confirmText = '确定',
  cancelText = '再想想',
  extraText,
  mood = 'sweat',
  onConfirm,
  onCancel,
  onExtra,
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
        <View className={`cfm-actions ${extraText ? 'stacked' : ''}`}>
          <View className='btn secondary cfm-btn' onClick={onCancel}>
            {cancelText}
          </View>
          {extraText ? (
            <View className='btn secondary cfm-btn' onClick={onExtra}>
              {extraText}
            </View>
          ) : null}
          <View className='btn cfm-btn' onClick={onConfirm}>
            {confirmText}
          </View>
        </View>
      </View>
    </View>
  )
}
