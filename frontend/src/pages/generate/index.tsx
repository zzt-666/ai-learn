import { useEffect, useRef, useState } from 'react'
import { View, Text, PageContainer } from '@tarojs/components'
import Taro, { useUnload } from '@tarojs/taro'
import ConfirmModal from '../../components/ConfirmModal'
import Mascot from '../../components/Mascot'
import {
  ApiError,
  cancelQuizTask,
  createQuizTask,
  getQuizTask,
  type QuizTaskPollResult,
} from '../../utils/api'
import { ensureLogin } from '../../utils/auth'
import { takePendingSourceText, setPendingSourceText } from '../../utils/pending'
import { saveSession } from '../../utils/storage'
import type { QuizSession } from '../../types/quiz'
import '../../styles/ui.scss'
import './index.scss'

type Phase = 'loading' | 'fail'

const POLL_INTERVAL_MS = 10000
/** Max wall time waiting for async task (well beyond WeChat single-request 60s). */
const POLL_MAX_MS = 5 * 60 * 1000

function sleep(ms: number) {
  return new Promise<void>((resolve) => {
    setTimeout(resolve, ms)
  })
}

export default function GeneratePage() {
  const [phase, setPhase] = useState<Phase>('loading')
  const [message, setMessage] = useState('出题翻车了')
  const [sourceText, setSourceText] = useState('')
  const [hint, setHint] = useState('正在创建出题任务…')
  const [leaveOpen, setLeaveOpen] = useState(false)
  /** Invisible PageContainer traps system / gesture / nav back. */
  const [backGuard, setBackGuard] = useState(true)
  /** User left / abandoned — never auto-enter quiz. */
  const abandonedRef = useRef(false)
  /** Successful handoff to quiz page — unload must not cancel. */
  const leavingForQuizRef = useRef(false)
  /** User confirmed leave via themed modal. */
  const confirmLeaveRef = useRef(false)
  const taskIdRef = useRef<number | null>(null)

  const abandonAndCancel = async () => {
    abandonedRef.current = true
    setBackGuard(false)
    const taskId = taskIdRef.current
    taskIdRef.current = null
    if (taskId == null) return
    try {
      await cancelQuizTask(taskId)
    } catch {
      // Best-effort: page is already leaving.
    }
  }

  const openLeaveConfirm = () => {
    if (leavingForQuizRef.current || phase === 'fail') return
    setBackGuard(false)
    setLeaveOpen(true)
  }

  const stayOnPage = () => {
    setLeaveOpen(false)
    confirmLeaveRef.current = false
    if (phase === 'loading' && !leavingForQuizRef.current) {
      setBackGuard(true)
    }
  }

  const confirmLeave = () => {
    confirmLeaveRef.current = true
    setLeaveOpen(false)
    void abandonAndCancel().finally(() => {
      Taro.navigateBack({ delta: 1 }).catch(() =>
        Taro.reLaunch({ url: '/pages/home/index' }),
      )
    })
  }

  const enterQuiz = (text: string, task: QuizTaskPollResult) => {
    if (abandonedRef.current) return
    if (!task.topic_name || !task.questions?.length) {
      throw new ApiError('GENERATE_FAILED', '出题结果不完整，请重试')
    }
    const session: QuizSession = {
      topic_name: task.topic_name,
      source_text: text,
      questions: task.questions,
      answers: [],
      current_index: 0,
      report: null,
      status: 'answering',
    }
    leavingForQuizRef.current = true
    setBackGuard(false)
    setLeaveOpen(false)
    saveSession(session)
    Taro.redirectTo({ url: '/pages/quiz/index' })
  }

  const pollUntilDone = async (taskId: number): Promise<QuizTaskPollResult> => {
    const started = Date.now()
    while (!abandonedRef.current) {
      const status = await getQuizTask(taskId)
      if (abandonedRef.current) {
        throw new ApiError('REQUEST_FAILED', '已取消出题')
      }
      if (status.status === 'succeeded') {
        return status
      }
      if (status.status === 'cancelled') {
        throw new ApiError('REQUEST_FAILED', '已取消出题')
      }
      if (status.status === 'failed') {
        throw new ApiError(
          'GENERATE_FAILED',
          status.error_message || '出题失败，请稍后重试',
        )
      }
      if (Date.now() - started > POLL_MAX_MS) {
        throw new ApiError(
          'UPSTREAM_TIMEOUT',
          '出题时间较长仍未完成，请稍后重试',
        )
      }
      setHint(
        status.status === 'running'
          ? '正在检索并出题，请稍候…'
          : '任务已排队，马上开始…',
      )
      await sleep(POLL_INTERVAL_MS)
    }
    throw new ApiError('REQUEST_FAILED', '已取消出题')
  }

  const runGenerate = async (text: string) => {
    abandonedRef.current = false
    leavingForQuizRef.current = false
    confirmLeaveRef.current = false
    taskIdRef.current = null
    setPhase('loading')
    setSourceText(text)
    setHint('正在创建出题任务…')
    setBackGuard(true)
    setLeaveOpen(false)
    Taro.setNavigationBarTitle({ title: '出题中' })
    try {
      await ensureLogin()
      if (abandonedRef.current) return
      const created = await createQuizTask({
        source_text: text,
        question_count: 6,
      })
      if (abandonedRef.current) {
        await cancelQuizTask(created.task_id).catch(() => undefined)
        return
      }
      taskIdRef.current = created.task_id
      setHint('任务已创建，正在检索并出题…')
      const done = await pollUntilDone(created.task_id)
      if (abandonedRef.current) return
      enterQuiz(text, done)
    } catch (err) {
      if (abandonedRef.current) return
      const msg =
        err instanceof ApiError
          ? err.message
          : '服务忙或模型没吐出合法题目。'
      setMessage(msg)
      setPhase('fail')
      setBackGuard(false)
      setLeaveOpen(false)
      Taro.setNavigationBarTitle({ title: '出题翻车' })
    }
  }

  useUnload(() => {
    if (leavingForQuizRef.current) return
    if (!confirmLeaveRef.current) {
      void abandonAndCancel()
    }
  })

  useEffect(() => {
    abandonedRef.current = false
    leavingForQuizRef.current = false
    const text = takePendingSourceText().trim()
    if (!text) {
      setMessage('没有收到学习材料，请回首页重新粘贴。')
      setPhase('fail')
      setBackGuard(false)
      Taro.setNavigationBarTitle({ title: '出题翻车' })
      return
    }
    runGenerate(text)
    return () => {
      if (!leavingForQuizRef.current) {
        abandonedRef.current = true
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const leaveModal = (
    <ConfirmModal
      open={leaveOpen}
      mood='sweat'
      title='要放弃这次出题吗？'
      message='离开后本次出题会彻底取消，后台生成也会中断。确定返回吗？'
      cancelText='再等等'
      confirmText='确定离开'
      onCancel={stayOnPage}
      onConfirm={confirmLeave}
    />
  )

  const backTrap =
    phase === 'loading' ? (
      <PageContainer
        show={backGuard}
        overlay={false}
        duration={0}
        position='center'
        zIndex={1}
        customStyle='width:0;height:0;opacity:0;overflow:hidden;'
        onBeforeLeave={() => {
          openLeaveConfirm()
        }}
      >
        <View />
      </PageContainer>
    ) : null

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
          onClick={() => {
            void abandonAndCancel().finally(() => {
              Taro.navigateBack({ delta: 1 }).catch(() =>
                Taro.reLaunch({ url: '/pages/home/index' }),
              )
            })
          }}
        >
          改材料重来
        </View>
        {leaveModal}
      </View>
    )
  }

  return (
    <View className='page-shell loading-page'>
      <View className='loading-wrap'>
        <Mascot mood='think' size='lg' />
        <View className='spinner' />
        <Text className='panel-title'>正在检索并出题…</Text>
        <Text className='hint loading-hint'>{hint}</Text>
        <View className='comic-bubble'>
          预计一会儿就好。你要是紧张，就先搓搓手。
        </View>
      </View>
      {backTrap}
      {leaveModal}
    </View>
  )
}
