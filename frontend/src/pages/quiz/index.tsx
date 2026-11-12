import { useMemo, useState } from 'react'
import { View, Text, ScrollView } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import CoinPill from '../../components/CoinPill'
import Mascot from '../../components/Mascot'
import type { Question, QuizSession, UserAnswer } from '../../types/quiz'
import { isCorrect, summarize } from '../../utils/grading'
import { ApiError, completeSession, generateReport } from '../../utils/api'
import { clearSession, loadSession, saveSession } from '../../utils/storage'
import '../../styles/ui.scss'
import './index.scss'

type TypeLabel = Record<string, string>

const TYPE_LABEL: TypeLabel = {
  single: '单选',
  multiple: '多选',
  boolean: '判断',
}

export default function QuizPage() {
  const [session, setSession] = useState<QuizSession | null>(null)
  const [selected, setSelected] = useState<number[]>([])
  const [feedback, setFeedback] = useState(false)
  const [viewIndex, setViewIndex] = useState(0)
  const [reporting, setReporting] = useState(false)

  useDidShow(() => {
    const s = loadSession()
    if (!s || !s.questions?.length) {
      Taro.showToast({ title: '没有进行中的闯关', icon: 'none' })
      Taro.reLaunch({ url: '/pages/home/index' })
      return
    }
    setSession(s)
    setViewIndex(s.current_index)
    const answered = s.answers[s.current_index]
    if (answered) {
      setSelected(answered.selected_indexes)
      setFeedback(true)
    } else {
      setSelected([])
      setFeedback(false)
    }
  })

  const question: Question | null = useMemo(() => {
    if (!session) return null
    return session.questions[viewIndex] || null
  }, [session, viewIndex])

  const total = session?.questions.length || 0
  const answeredCount = session?.answers.length || 0
  const isReviewingPast = viewIndex < answeredCount
  const canSubmit =
    !!question &&
    !feedback &&
    !isReviewingPast &&
    (question.type === 'multiple' ? selected.length >= 1 : selected.length === 1)

  const persist = (next: QuizSession) => {
    setSession(next)
    saveSession(next)
  }

  const toggleOption = (idx: number) => {
    if (!question || feedback || isReviewingPast) return
    if (question.type === 'multiple') {
      setSelected((prev) =>
        prev.includes(idx) ? prev.filter((i) => i !== idx) : [...prev, idx],
      )
      return
    }
    // 单选 / 判断：选中即提交
    const nextSelected = [idx]
    setSelected(nextSelected)
    submitAnswer(nextSelected)
  }

  const submitAnswer = (indexes: number[] = selected) => {
    if (!session || !question || feedback || isReviewingPast) return
    if (question.type === 'multiple' && indexes.length < 1) {
      Taro.showToast({ title: '请至少选择一项', icon: 'none' })
      return
    }
    const correct = isCorrect(question.answer_indexes, indexes)
    const answer: UserAnswer = {
      question_id: question.id,
      selected_indexes: [...new Set(indexes)].sort((a, b) => a - b),
      is_correct: correct,
    }
    const answers = [...session.answers]
    answers[viewIndex] = answer
    const next: QuizSession = {
      ...session,
      answers,
      current_index: viewIndex,
    }
    persist(next)
    setFeedback(true)
  }

  const goPrev = () => {
    if (!session || viewIndex <= 0) return
    const prev = viewIndex - 1
    setViewIndex(prev)
    const ans = session.answers[prev]
    setSelected(ans?.selected_indexes || [])
    setFeedback(Boolean(ans))
  }

  const goNext = async () => {
    if (!session) return
    if (viewIndex < total - 1) {
      const nextIdx = viewIndex + 1
      setViewIndex(nextIdx)
      const ans = session.answers[nextIdx]
      if (ans) {
        setSelected(ans.selected_indexes)
        setFeedback(true)
      } else {
        setSelected([])
        setFeedback(false)
        persist({ ...session, current_index: nextIdx })
      }
      return
    }
    // 最后一题 → 生成报告
    await finishAndReport(session)
  }

  const finishAndReport = async (s: QuizSession) => {
    if (reporting) return
    setReporting(true)
    const stats = summarize(s.answers)
    const items = s.questions.map((q, i) => {
      const a = s.answers[i]
      return {
        question_id: q.id,
        type: q.type,
        stem: q.stem,
        options: q.options,
        answer_indexes: q.answer_indexes,
        selected_indexes: a?.selected_indexes || [],
        is_correct: Boolean(a?.is_correct),
        explanation: q.explanation,
      }
    })
    try {
      persist({ ...s, status: 'reporting' })
      const report = await generateReport({
        topic_name: s.topic_name,
        source_text_excerpt: s.source_text.slice(0, 2000),
        correct_count: stats.correct_count,
        wrong_count: stats.wrong_count,
        accuracy: stats.accuracy,
        items,
      })
      let next: typeof s = { ...s, report, status: 'done', pending_complete: true }
      persist(next)
      try {
        const completed = await completeSession({
          topic_name: s.topic_name,
          source_text: s.source_text,
          questions: s.questions,
          answers: s.answers,
          report,
          source_session_id: s.source_session_id ?? null,
        })
        next = {
          ...next,
          session_id: completed.session_id,
          exp_gained: completed.exp_gained,
          points_gained: completed.points_gained,
          pending_complete: false,
        }
        persist(next)
      } catch (completeErr) {
        const cmsg =
          completeErr instanceof ApiError
            ? completeErr.message
            : '记录保存失败，可稍后在报告页重试'
        Taro.showToast({ title: cmsg, icon: 'none', duration: 2500 })
      }
      Taro.redirectTo({ url: '/pages/report/index' })
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '报告生成失败'
      Taro.showModal({
        title: '报告翻车了',
        content: msg,
        confirmText: '再试一次',
        cancelText: '回首页',
        success: (res) => {
          if (res.confirm) finishAndReport(s)
          else {
            clearSession()
            Taro.reLaunch({ url: '/pages/home/index' })
          }
        },
      })
    } finally {
      setReporting(false)
    }
  }

  if (!session || !question) {
    return <View className='page-shell quiz-mode' />
  }

  const currentAnswer = session.answers[viewIndex]
  const isCorrectNow = currentAnswer?.is_correct
  const showFooter = feedback || question.type === 'multiple'

  return (
    <View className='page-shell quiz-mode'>
      {reporting ? (
        <View className='report-loading'>
          <Mascot mood='think' size='lg' />
          <View className='spinner' />
          <Text className='panel-title'>题答完了，正在写复盘…</Text>
          <Text className='hint'>正确率、错题回顾、薄弱点，马上端上来。</Text>
        </View>
      ) : (
        <>
          <ScrollView scrollY className='quiz-screen'>
            <View className='quiz-top'>
              <View
                className='quiz-icon-btn'
                onClick={() =>
                  Taro.showModal({
                    title: '退出本局？',
                    content: '本期不支持断点续玩，退出后需重新开局。',
                    success: (res) => {
                      if (res.confirm) {
                        clearSession()
                        Taro.reLaunch({ url: '/pages/home/index' })
                      }
                    },
                  })
                }
              >
                ×
              </View>
              <View className='quiz-index-badge'>
                <Text>
                  {viewIndex + 1}/{total}
                </Text>
              </View>
              <CoinPill value={360} />
            </View>

            <View className='quiz-topic'>
              <Mascot
                mood={feedback ? (isCorrectNow ? 'happy' : 'sweat') : 'think'}
                size='sm'
              />
              <View>
                <Text className='topic-name'>{session.topic_name}</Text>
                <Text className='hint'>
                  {TYPE_LABEL[question.type]} · {feedback ? '已判题' : '材料闯关'}
                </Text>
              </View>
            </View>

            <Text className='quiz-progress'>
              第 {viewIndex + 1} 题 / 共 {total} 题
            </Text>
            <Text className='quiz-stem'>{question.stem}</Text>

            <View className='quiz-options'>
              {question.options.map((opt, idx) => {
                const classes = ['quiz-opt']
                if (!feedback && selected.includes(idx)) classes.push('selected')
                if (feedback) {
                  const isAns = question.answer_indexes.includes(idx)
                  const isSel = selected.includes(idx)
                  if (isAns) classes.push('correct', 'judged')
                  else if (isSel) classes.push('wrong', 'judged')
                }
                return (
                  <View
                    key={`${question.id}-${idx}`}
                    className={classes.join(' ')}
                    onClick={() => toggleOption(idx)}
                  >
                    {feedback && (question.answer_indexes.includes(idx) || selected.includes(idx)) ? (
                      <Text className='dot'>
                        {question.answer_indexes.includes(idx) ? '✓' : '✗'}
                      </Text>
                    ) : null}
                    <Text>{opt}</Text>
                  </View>
                )
              })}
            </View>

            {feedback ? (
              <>
                <View className={`result-banner ${isCorrectNow ? 'ok' : 'bad'}`}>
                  <Mascot mood={isCorrectNow ? 'happy' : 'sweat'} size='tiny' />
                  <View className='grow'>
                    <Text>{isCorrectNow ? '漂亮，拿下！ · 答对了' : '差一点点！ · 答错了'}</Text>
                    <View className='gain-line'>
                      <Text className='xp-gain'>{isCorrectNow ? '+20 EXP' : '+5 EXP（参与奖）'}</Text>
                      <Text className='coin-gain'>{isCorrectNow ? '+5 积分' : '积分无加成'}</Text>
                    </View>
                  </View>
                </View>
                <View className={`feedback-sheet ${isCorrectNow ? 'ok' : 'bad'}`}>
                  <Text className='sheet-title'>知识讲解</Text>
                  <Text className='sheet-body'>
                    正确答案：
                    {question.answer_indexes.map((i) => question.options[i]).join('、')}
                    {'\n'}
                    {question.explanation}
                  </Text>
                </View>
              </>
            ) : null}
          </ScrollView>

          {showFooter ? (
            <View className='quiz-footer'>
              {feedback ? (
                <View className='btn-row'>
                  <View className={`btn secondary ${viewIndex === 0 ? 'disabled' : ''}`} onClick={goPrev}>
                    上一题
                  </View>
                  <View className='btn' onClick={goNext}>
                    {viewIndex >= total - 1 ? '查看报告 →' : '下一题 →'}
                  </View>
                </View>
              ) : (
                <View
                  className={`btn ${canSubmit ? '' : 'disabled'}`}
                  onClick={() => submitAnswer()}
                >
                  提交答案
                </View>
              )}
            </View>
          ) : null}
        </>
      )}
    </View>
  )
}
