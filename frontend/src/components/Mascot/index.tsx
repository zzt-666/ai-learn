import { View, Image } from '@tarojs/components'
import './index.scss'

type Mood = 'idle' | 'happy' | 'sweat' | 'think' | 'cheer'
type Size = 'tiny' | 'sm' | 'md' | 'lg'

const FACES: Record<Mood, string> = {
  idle: `
    <circle cx="48" cy="34" r="3.2" fill="#1a1a1a"/>
    <circle cx="72" cy="34" r="3.2" fill="#1a1a1a"/>
    <path d="M52 46 Q60 52 68 46" fill="none" stroke="#1a1a1a" stroke-width="2.4" stroke-linecap="round"/>
  `,
  happy: `
    <path d="M42 34 Q48 28 54 34" fill="none" stroke="#1a1a1a" stroke-width="2.6" stroke-linecap="round"/>
    <path d="M66 34 Q72 28 78 34" fill="none" stroke="#1a1a1a" stroke-width="2.6" stroke-linecap="round"/>
    <path d="M50 46 Q60 56 70 46" fill="none" stroke="#1a1a1a" stroke-width="2.6" stroke-linecap="round"/>
    <circle cx="38" cy="42" r="4" fill="#ff9aa2" opacity=".85"/>
    <circle cx="82" cy="42" r="4" fill="#ff9aa2" opacity=".85"/>
  `,
  sweat: `
    <circle cx="48" cy="34" r="3.2" fill="#1a1a1a"/>
    <circle cx="72" cy="34" r="3.2" fill="#1a1a1a"/>
    <path d="M54 48 Q60 44 66 48" fill="none" stroke="#1a1a1a" stroke-width="2.4" stroke-linecap="round"/>
    <path d="M86 22 Q90 14 94 22 Q90 28 86 22Z" fill="#7ec8e3" stroke="#1a1a1a" stroke-width="2"/>
  `,
  think: `
    <circle cx="48" cy="34" r="3.2" fill="#1a1a1a"/>
    <circle cx="72" cy="34" r="3.2" fill="#1a1a1a"/>
    <circle cx="60" cy="48" r="2.2" fill="#1a1a1a"/>
    <circle cx="92" cy="18" r="3" fill="none" stroke="#1a1a1a" stroke-width="2"/>
    <circle cx="100" cy="10" r="2" fill="none" stroke="#1a1a1a" stroke-width="1.6"/>
  `,
  cheer: `
    <path d="M42 36 Q48 30 54 36" fill="none" stroke="#1a1a1a" stroke-width="2.6" stroke-linecap="round"/>
    <path d="M66 36 Q72 30 78 36" fill="none" stroke="#1a1a1a" stroke-width="2.6" stroke-linecap="round"/>
    <path d="M48 48 Q60 62 72 48" fill="none" stroke="#1a1a1a" stroke-width="2.8" stroke-linecap="round"/>
    <path d="M24 70 L16 52" stroke="#1a1a1a" stroke-width="3" stroke-linecap="round"/>
    <path d="M96 70 L104 52" stroke="#1a1a1a" stroke-width="3" stroke-linecap="round"/>
  `,
}

function toDataUri(mood: Mood) {
  const face = FACES[mood] || FACES.idle
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120">
  <ellipse cx="60" cy="108" rx="28" ry="6" fill="#1a1a1a" opacity=".12"/>
  <path d="M28 42c0-22 16-36 32-36s32 14 32 36c0 4-1 8-2 11H30c-1-3-2-7-2-11z" fill="#6b3f24" stroke="#1a1a1a" stroke-width="2.5"/>
  <path d="M34 28c4-6 8-8 12-8M54 18c6-4 14-4 20 0M78 24c4 0 8 3 10 7" fill="none" stroke="#1a1a1a" stroke-width="2" stroke-linecap="round"/>
  <ellipse cx="60" cy="48" rx="28" ry="26" fill="#ffd7b5" stroke="#1a1a1a" stroke-width="2.5"/>
  ${face}
  <path d="M28 78c8-10 20-14 32-14s24 4 32 14l6 28H22l6-28z" fill="#ff9f3c" stroke="#1a1a1a" stroke-width="2.5" stroke-linejoin="round"/>
  <path d="M48 72v20M72 72v20" stroke="#1a1a1a" stroke-width="2"/>
  <path d="M40 92h40" stroke="#1a1a1a" stroke-width="2" stroke-linecap="round"/>
  <circle cx="54" cy="84" r="2" fill="#1a1a1a"/>
  <circle cx="66" cy="84" r="2" fill="#1a1a1a"/>
  <path d="M54 86v10M66 86v10" stroke="#1a1a1a" stroke-width="1.6"/>
</svg>`
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`
}

interface Props {
  mood?: Mood
  size?: Size
}

export default function Mascot({ mood = 'idle', size = 'md' }: Props) {
  return (
    <View className={`mascot mascot-${size}`}>
      <Image className='mascot-img' src={toDataUri(mood)} mode='aspectFit' />
    </View>
  )
}
