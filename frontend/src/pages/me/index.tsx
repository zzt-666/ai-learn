import { useRef, useState } from 'react'
import { View, Text, Input, Button, Image } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import Mascot from '../../components/Mascot'
import TabBar from '../../components/TabBar'
import type { UserPublic } from '../../types/user'
import { ApiError, fetchMe, updateNickname, uploadAvatar } from '../../utils/api'
import { ensureLogin, getCachedUser, isLoggedIn, logoutLocal } from '../../utils/auth'
import { resolveAvatarUrl } from '../../utils/avatar'
import '../../styles/ui.scss'
import './index.scss'

export default function MePage() {
  const [user, setUser] = useState<UserPublic | null>(null)
  const [nicknameDraft, setNicknameDraft] = useState('阿衰同学')
  const [editingNick, setEditingNick] = useState(false)
  const [saving, setSaving] = useState(false)
  const [loginError, setLoginError] = useState('')
  const draftRef = useRef('阿衰同学')
  const savedNickRef = useRef('阿衰同学')
  const savingNickRef = useRef(false)

  const syncNicknameLocal = (name: string) => {
    setNicknameDraft(name)
    draftRef.current = name
    savedNickRef.current = name
  }

  const load = async () => {
    try {
      await ensureLogin()
      const fresh = await fetchMe()
      setUser(fresh)
      syncNicknameLocal(fresh.nickname)
      setLoginError('')
    } catch (err) {
      const cached = getCachedUser()
      setUser(cached)
      syncNicknameLocal(cached?.nickname || '阿衰同学')
      setLoginError(err instanceof ApiError ? err.message : '登录失败，请重试')
    }
  }

  useDidShow(() => {
    const cached = getCachedUser()
    if (cached) {
      setUser(cached)
      syncNicknameLocal(cached.nickname)
    }
    load()
  })

  const onChooseAvatar = async (e: { detail?: { avatarUrl?: string } }) => {
    const path = e.detail?.avatarUrl
    if (!path) return
    try {
      setSaving(true)
      const u = await uploadAvatar(path)
      setUser(u)
      Taro.showToast({ title: '头像已保存', icon: 'success' })
    } catch (err) {
      Taro.showToast({
        title: err instanceof ApiError ? err.message : '头像保存失败',
        icon: 'none',
      })
    } finally {
      setSaving(false)
    }
  }

  /** 失焦后的统一保存：有变化才请求并提示，无变化静默返回 */
  const saveNickname = async (raw?: string) => {
    const name = (raw ?? draftRef.current).trim()
    setEditingNick(false)
    if (!name) {
      syncNicknameLocal(savedNickRef.current || '阿衰同学')
      Taro.showToast({ title: '昵称不能为空', icon: 'none' })
      return
    }
    if (name === savedNickRef.current) return
    if (savingNickRef.current) return
    savingNickRef.current = true
    try {
      setSaving(true)
      const u = await updateNickname(name)
      setUser(u)
      syncNicknameLocal(u.nickname)
      Taro.showToast({ title: '昵称已保存', icon: 'success' })
    } catch (err) {
      Taro.showToast({
        title: err instanceof ApiError ? err.message : '保存失败',
        icon: 'none',
      })
    } finally {
      savingNickRef.current = false
      setSaving(false)
    }
  }

  const logout = () => {
    logoutLocal()
    setUser(null)
    syncNicknameLocal('阿衰同学')
    Taro.showToast({ title: '已退出，需重新登录才能闯关', icon: 'none' })
  }

  const loggedIn = isLoggedIn() && user
  const expWithin = user ? user.exp % 300 : 0
  const progressPct = user ? Math.round(user.level_progress * 100) : 0
  const avatar = resolveAvatarUrl(user?.avatar_url)

  return (
    <View className='page-shell'>
      <View className='page-body me-body'>
        {loginError && !loggedIn ? (
          <View className='comic-panel'>
            <Text className='panel-title'>还没登录上</Text>
            <Text className='hint warn'>{loginError}</Text>
            <View className='btn secondary' onClick={load}>
              重试登录
            </View>
          </View>
        ) : null}

        <View className='me-hero'>
          <Button className='avatar-btn' openType='chooseAvatar' onChooseAvatar={onChooseAvatar}>
            {avatar ? (
              <Image className='avatar-img' src={avatar} mode='aspectFill' />
            ) : (
              <Mascot mood='idle' size='sm' />
            )}
          </Button>
          <View className='grow'>
            <Input
              className={`nickname-input ${editingNick ? 'editing' : ''}`}
              type='nickname'
              maxlength={32}
              value={nicknameDraft}
              placeholder='阿衰同学'
              onFocus={() => setEditingNick(true)}
              onInput={(e) => {
                // 主动输入：只更新本地，不发请求
                const value = e.detail.value
                setNicknameDraft(value)
                draftRef.current = value
              }}
              onChange={(e) => {
                // 选用微信昵称时经常不走 onInput，会走 change
                const value = e.detail.value
                setNicknameDraft(value)
                draftRef.current = value
                Taro.hideKeyboard({
                  complete: () => {
                    void saveNickname(value)
                  },
                })
              }}
              onNickNameReview={() => {
                // 选用微信昵称后会触发审核；强制收起键盘失焦，由 onBlur 带出最新值并保存
                Taro.hideKeyboard({
                  complete: () => {
                    void saveNickname(draftRef.current)
                  },
                })
              }}
              onBlur={(e) => {
                const value = e.detail.value
                setNicknameDraft(value)
                draftRef.current = value
                void saveNickname(value)
              }}
            />
            <Text className='hint'>
              {loggedIn
                ? `已绑定微信 · 累计通关 ${user?.completed_count ?? 0} 局`
                : '未登录 · 登录后才能闯关'}
            </Text>
            {saving ? <Text className='hint'>保存中…</Text> : null}
          </View>
        </View>

        <View className='level-card'>
          <View className='lv-badge'>
            <Text>Lv</Text>
            <Text>{user?.level ?? 1}</Text>
          </View>
          <View className='grow'>
            <Text className='lv-exp'>经验值 {expWithin} / 300</Text>
            <View className='xp-track'>
              <View className='xp-fill' style={{ width: `${progressPct}%` }} />
            </View>
            <View className='reward-row'>
              <Text className='pill coin'>积分 {user?.points ?? 0}</Text>
              <Text className='hint'>
                再攒 {user?.exp_to_next_level ?? 300} EXP 升 Lv.{(user?.level ?? 1) + 1}
              </Text>
            </View>
          </View>
        </View>

        <View
          className='list-item'
          onClick={() => {
            if (!loggedIn) {
              Taro.showToast({ title: '请先登录', icon: 'none' })
              return
            }
            Taro.navigateTo({ url: '/pages/history/index' })
          }}
        >
          <View className='meta'>
            <Text className='meta-title'>闯关历史</Text>
            <Text className='meta-sub'>通关报告 · 重闯记录</Text>
          </View>
        </View>

        <View
          className='list-item'
          onClick={() => Taro.showToast({ title: '即将上线', icon: 'none' })}
        >
          <View className='meta'>
            <Text className='meta-title'>学习偏好</Text>
            <Text className='meta-sub'>默认 6 题 · 标准难度</Text>
          </View>
        </View>

        <View
          className='list-item'
          onClick={() => Taro.showToast({ title: '示意入口，商业化后置', icon: 'none' })}
        >
          <View className='meta'>
            <Text className='meta-title'>积分怎么用？（示意）</Text>
            <Text className='meta-sub'>换题量加成 / 皮肤贴纸 · 商业化后置</Text>
          </View>
        </View>

        <View className='list-item'>
          <View className='meta'>
            <Text className='meta-title'>关于衰衰闯关</Text>
            <Text className='meta-sub'>版本 v0.2 · 用户系统</Text>
          </View>
        </View>

        <View className='btn secondary mt-auto' onClick={logout}>
          退出登录
        </View>
      </View>
      <TabBar active='me' />
    </View>
  )
}
