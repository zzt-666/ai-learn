import { useState } from 'react'
import { View, Text, Textarea, Image } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import CoinPill from '../../components/CoinPill'
import Mascot from '../../components/Mascot'
import TabBar from '../../components/TabBar'
import type { HistoryItem, UserPublic } from '../../types/user'
import { ApiError, fetchHistory } from '../../utils/api'
import { ensureLogin, getCachedUser, isLoggedIn } from '../../utils/auth'
import { resolveAvatarUrl } from '../../utils/avatar'
import { accuracyPercent } from '../../utils/format'
import { setPendingQuizStart } from '../../utils/pending'
import { resumeUnfinishedSession, toastResumeError } from '../../utils/resumeSession'
import { settleFullyAnsweredSessions } from '../../utils/silentFinish'
import { hasSeenGuide, markGuideSeen } from '../../utils/storage'
import '../../styles/ui.scss'
import './index.scss'

export default function HomePage() {
  const [showGuide, setShowGuide] = useState(false)
  const [sourceText, setSourceText] = useState('')
  const [emptyWarn, setEmptyWarn] = useState(false)
  const [user, setUser] = useState<UserPublic | null>(null)
  const [loginError, setLoginError] = useState('')
  const [loggingIn, setLoggingIn] = useState(false)
  const [recent, setRecent] = useState<HistoryItem[]>([])
  const [unfinished, setUnfinished] = useState<HistoryItem[]>([])

  const refresh = async () => {
    setLoggingIn(true)
    setLoginError('')
    try {
      const u = await ensureLogin()
      setUser(u)
      try {
        let inProgress = await fetchHistory(50, { status: 'in_progress' })
        if (await settleFullyAnsweredSessions(inProgress)) {
          inProgress = await fetchHistory(50, { status: 'in_progress' })
        }
        const completed = await fetchHistory(2, { status: 'completed' })
        setRecent(completed.slice(0, 2))
        setUnfinished(inProgress.slice(0, 3))
      } catch {
        setRecent([])
        setUnfinished([])
      }
    } catch (err) {
      setUser(null)
      setRecent([])
      setUnfinished([])
      setLoginError(err instanceof ApiError ? err.message : '登录失败，请重试')
    } finally {
      setLoggingIn(false)
    }
  }

  useDidShow(() => {
    setShowGuide(!hasSeenGuide())
    const cached = getCachedUser()
    if (cached) setUser(cached)
    refresh()
  })

  const dismissGuide = () => {
    markGuideSeen()
    setShowGuide(false)
  }

  const startQuiz = async () => {
    const text = sourceText.trim()
    if (!text) {
      setEmptyWarn(true)
      Taro.showToast({ title: '先贴点东西再开局', icon: 'none' })
      return
    }
    if (!isLoggedIn()) {
      Taro.showToast({
        title: loggingIn ? '正在登录…' : '请先登录后再闯关',
        icon: 'none',
      })
      if (!loggingIn) await refresh()
      return
    }
    setEmptyWarn(false)
    setPendingQuizStart({ source_text: text })
    Taro.navigateTo({ url: '/pages/generate/index' })
  }

  const onResume = async (item: HistoryItem) => {
    try {
      await resumeUnfinishedSession(item.id)
    } catch (err) {
      toastResumeError(err, '无法继续闯关')
    }
  }

  if (showGuide) {
    return (
      <View className='page-shell guide-page'>
        <View className='guide-main'>
          <Mascot mood='cheer' size='lg' />
          <Text className='guide-title'>衰衰闯关</Text>
          <Text className='guide-sub'>粘一段 → 开一局 → 边答边学</Text>
          <View className='comic-bubble guide-bubble'>
            哟，别光「看过」就完事。把笔记砸给我，我给你整套闯关题——答完还有复盘报告，兄弟罩你。
          </View>
        </View>
        <View className='guide-bottom'>
          <View className='btn guide-btn' onClick={dismissGuide}>
            开整！去粘贴 →
          </View>
          <Text className='hint'>约 1 分钟搞懂怎么玩</Text>
        </View>
      </View>
    )
  }

  const nickname = user?.nickname || '阿衰同学'
  const avatar = resolveAvatarUrl(user?.avatar_url)

  return (
    <View className='page-shell'>
      <View className='page-body home-body'>
        <View className='home-head'>
          <View className='hello-row'>
            {avatar ? (
              <Image className='home-avatar' src={avatar} mode='aspectFill' />
            ) : (
              <View className='home-avatar home-avatar-default'>
                <Mascot mood='idle' size='tiny' />
              </View>
            )}
            <Text className='hello-inline'>你好呀，{nickname}</Text>
          </View>
          <CoinPill value={user?.points ?? 0} />
        </View>

        {loginError ? (
          <View className='comic-panel login-fail'>
            <Text className='panel-title'>登录没成功</Text>
            <Text className='hint warn'>{loginError}</Text>
            <View className='btn secondary' onClick={refresh}>
              重试登录
            </View>
          </View>
        ) : null}

        {loggingIn && !user ? <Text className='hint'>正在静默登录…</Text> : null}

        <View className='home-title-row'>
          <Text className='home-title'>今天想闯哪一关？</Text>
          <Mascot mood='idle' size='sm' />
        </View>

        <View className='stack'>
          <Text className='field-label'>粘贴学习材料</Text>
          <Textarea
            className={`textarea ${emptyWarn ? 'error' : ''}`}
            placeholder='粘贴一句话 / 一段笔记 / 长文本…主题名由 AI 自动生成'
            maxlength={8000}
            value={sourceText}
            onInput={(e) => {
              setSourceText(e.detail.value)
              if (e.detail.value.trim()) setEmptyWarn(false)
            }}
            autoHeight
          />
          {emptyWarn ? (
            <Text className='hint warn'>先贴点东西再开局——空着手我变不出题来。</Text>
          ) : null}
        </View>

        <View className='btn' onClick={startQuiz}>
          开始闯关！
        </View>

        <Text className='section-label'>直接开闯</Text>
        {recent.length === 0 ? (
          <Text className='hint'>通关后，最近两局会出现在这里，点一下就能重闯。</Text>
        ) : (
          <View className='quick-picks'>
            {recent.map((item) => (
              <View
                key={item.id}
                className='quick-pick'
                onClick={() =>
                  Taro.navigateTo({ url: `/pages/history/report?id=${item.id}` })
                }
              >
                <Text className='qp-title'>{item.topic_name}</Text>
                <Text className='qp-sub'>
                  正确率：{accuracyPercent(item.accuracy)}% · {item.question_count || 0}题
                </Text>
                <Text className='qp-cta'>直接开闯</Text>
              </View>
            ))}
          </View>
        )}

        <Text className='section-label'>未完成的闯关</Text>
        {unfinished.length === 0 ? (
          <Text className='hint'>暂无未完成闯关。开一局答到一半退出，就会出现在这里。</Text>
        ) : (
          <View className='unfinished'>
            {unfinished.map((item) => {
              const answered = item.answered_count ?? 0
              const total = item.question_count || 0
              const pct = total > 0 ? Math.round((answered / total) * 100) : 0
              return (
                <View
                  key={item.id}
                  className='unfinished-item'
                  onClick={() => void onResume(item)}
                >
                  <View className='ico'>
                    <Mascot mood='think' size='tiny' />
                  </View>
                  <View className='meta'>
                    <Text className='meta-title'>{item.topic_name}</Text>
                    <Text className='meta-sub'>
                      {answered}/{total} 题 · 继续闯关
                    </Text>
                  </View>
                  <View className='ring-text'>
                    <View
                      className='ring-svg'
                      style={{
                        backgroundImage: `url("data:image/svg+xml,${encodeURIComponent(
                          `<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 80 80'><circle cx='40' cy='40' r='30' fill='none' stroke='#ffe2c4' stroke-width='6'/><circle cx='40' cy='40' r='30' fill='none' stroke='#ff9f3c' stroke-width='6' stroke-linecap='round' transform='rotate(-90 40 40)' stroke-dasharray='${2 * Math.PI * 30}' stroke-dashoffset='${2 * Math.PI * 30 * (1 - pct / 100)}'/></svg>`,
                        )}")`,
                      }}
                    />
                    <Text className='ring-num'>{pct}%</Text>
                  </View>
                </View>
              )
            })}
          </View>
        )}
      </View>
      <TabBar active='home' />
    </View>
  )
}
