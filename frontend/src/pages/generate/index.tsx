import { useEffect, useState } from 'react'
import { View, Text } from '@tarojs/components'
import Taro from '@tarojs/taro'
import Mascot from '../../components/Mascot'
import { ApiError, generateQuiz } from '../../utils/api'
import { takePendingSourceText, setPendingSourceText } from '../../utils/pending'
import { saveSession } from '../../utils/storage'
import type { QuizSession } from '../../types/quiz'
import '../../styles/ui.scss'
import './index.scss'

type Phase = 'loading' | 'fail'

export default function GeneratePage() {
  const [phase, setPhase] = useState<Phase>('loading')
  const [message, setMessage] = useState('出题翻车了')
  const [sourceText, setSourceText] = useState('')

  const runGenerate = async (text: string) => {
    setPhase('loading')
    setSourceText(text)
    try {
      const quiz = await generateQuiz({
        source_text: text,
        question_count: 6,
      })
      const session: QuizSession = {
        topic_name: quiz.topic_name,
        source_text: text,
        questions: quiz.questions,
        answers: [],
        current_index: 0,
        report: null,
        status: 'answering',
      }
      saveSession(session)
      Taro.redirectTo({ url: '/pages/quiz/index' })
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? err.message
          : '服务忙或模型没吐出合法题目。'
      setMessage(msg)
      setPhase('fail')
    }
  }

  useEffect(() => {
    const text = takePendingSourceText().trim()
    if (!text) {
      setMessage('没有收到学习材料，请回首页重新粘贴。')
      setPhase('fail')
      return
    }
    runGenerate(text)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (phase === 'fail') {
    return (
      <View className='page-shell fail-page'>
        <Mascot mood='sweat' size='lg' />
        <View className='comic-panel'>
          <Text className='panel-title'>出题翻车了</Text>
          <Text className='fail-desc'>
            原因：{message}
            {'\n\n'}
            你可以：稍后再试，或改改材料重来。
          </Text>
        </View>
        <View
          className='btn'
          onClick={() => {
            if (!sourceText.trim()) {
              Taro.reLaunch({ url: '/pages/home/index' })
              return
            }
            setPendingSourceText(sourceText)
            runGenerate(sourceText)
          }}
        >
          再试一次
        </View>
        <View
          className='btn secondary'
          onClick={() =>
            Taro.navigateBack({ delta: 1 }).catch(() =>
              Taro.reLaunch({ url: '/pages/home/index' }),
            )
          }
        >
          改材料重来
        </View>
      </View>
    )
  }

  return (
    <View className='page-shell loading-page'>
      <View className='loading-wrap'>
        <Mascot mood='think' size='lg' />
        <View className='spinner' />
        <Text className='panel-title'>正在根据你的材料出题…</Text>
        <Text className='hint loading-hint'>
          单选、多选、判断混着来。别刷新，小衰脑子转得慢但稳。
        </Text>
        <View className='comic-bubble'>预计一会儿就好。你要是紧张，就先搓搓手。</View>
      </View>
    </View>
  )
}
