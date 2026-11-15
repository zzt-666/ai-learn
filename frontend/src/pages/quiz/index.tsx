import { useEffect, useMemo, useState } from 'react'
import { View, Text, ScrollView } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import CoinPill from '../../components/CoinPill'
import Mascot from '../../components/Mascot'
import type { Question, QuizSession, UserAnswer } from '../../types/quiz'
import { ApiError, fetchQuestionExplanation } from '../../utils/api'
import { isCorrect } from '../../utils/grading'
import { getCachedUser } from '../../utils/auth'
import {
  EXP_PER_CORRECT,
  EXP_PER_WRONG,
  POINTS_PER_CORRECT,
  calcSessionRewards,
} from '../../utils/rewards'
import { loadSession, saveSession } from '../../utils/storage'
import '../../styles/ui.scss'
import './index.scss'

function parseKbQuestionId(id: string): number | null {
  const m = /^kbq-(\d+)$/.exec(id || '')
  return m ? Number(m[1]) : null
}

function needsAiExplanation(q: Question | null): boolean {
  if (!q) return false
  const text = (q.explanation || '').trim()
  if (!text || text === '暂无解析') return true
  if (q.explanation_source === 'none') return true
  return false
}

type TypeLabel = Record<string, string>

const TYPE_LABEL: TypeLabel = {
  single: '单选',
  multiple: '多选',
  boolean: '判断',
}

function truncateTitle(title: string, max = 14): string {
  if (title.length <= max) return title
  return `${title.slice(0, max)}…`
}

export default function QuizPage() {
  const [session, setSession] = useState<QuizSession | null>(null)
  const [selected, setSelected] = useState<number[]>([])
  const [feedback, setFeedback] = useState(false)
  const [viewIndex, setViewIndex] = useState(0)
  const [basePoints, setBasePoints] = useState(0)
  const [explainLoading, setExplainLoading] = useState(false)

  useDidShow(() => {
    const s = loadSession()
    if (!s || !s.questions?.length) {
      Taro.showToast({ title: '没有进行中的闯关', icon: 'none' })
      Taro.reLaunch({ url: '/pages/home/index' })
      return
    }
    // Already finished reporting elsewhere — bounce to report.
    if (s.report || s.status === 'reporting' || s.status === 'done') {
      Taro.redirectTo({ url: '/pages/report/index' })
      return
    }
    setSession(s)
    setViewIndex(s.current_index)
    Taro.setNavigationBarTitle({ title: truncateTitle(s.topic_name) })
    setBasePoints(getCachedUser()?.points ?? 0)
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

  useEffect(() => {
    if (!feedback || !session || !question) return
    if (!needsAiExplanation(question)) return
    const kbId = session.knowledge_base_id
    const qid = parseKbQuestionId(question.id)
    if (!kbId || qid == null) return

    let cancelled = false
    setExplainLoading(true)
    void fetchQuestionExplanation(kbId, qid)
      .then((res) => {
        if (cancelled) return
        const text = (res.explanation || '').trim()
        if (!text) return
        const questions = session.questions.map((q, i) =>
          i === viewIndex
            ? {
                ...q,
                explanation: text,
                explanation_source: res.explanation_source,
              }
            : q,
        )
        persist({ ...session, questions })
      })
      .catch((err) => {
        if (!cancelled && err instanceof ApiError) {
          // Keep 暂无解析; do not block the round.
        }
      })
      .finally(() => {
        if (!cancelled) setExplainLoading(false)
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [feedback, viewIndex, question?.id, session?.knowledge_base_id])

  const total = session?.questions.length || 0
  const answeredCount = session?.answers.length || 0
  const correctSoFar = useMemo(
    () => (session?.answers || []).filter((a) => a?.is_correct).length,
    [session?.answers],
  )
  const sessionPreview = useMemo(
    () => calcSessionRewards(correctSoFar, total),
    [correctSoFar, total],
  )
  const displayPoints = basePoints + sessionPreview.pointsGained
  const isReviewingPast = viewIndex < answeredCount
  const canSubmit =
    !!question &&
    !feedback &&
    !isReviewingPast &&
    (question.type === 'multiple' ? selected.length >= 1 : selected.length === 1)
  const progressPct = total > 0 ? Math.round(((viewIndex + 1) / total) * 100) : 0

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

  const goNext = () => {
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
    // Last question: enter report page; generation starts there (not before click).
    persist({ ...session, status: 'reporting' })
    Taro.redirectTo({ url: '/pages/report/index' })
  }

  if (!session || !question) {
    return <View className='page-shell quiz-mode' />
  }

  const currentAnswer = session.answers[viewIndex]
  const isCorrectNow = currentAnswer?.is_correct
  const showFooter = feedback || question.type === 'multiple'

  return (
    <View className='page-shell quiz-mode'>
      <ScrollView scrollY className='quiz-screen'>
        <View className='quiz-meta-row'>
          <Text className='hint'>
            {TYPE_LABEL[question.type]} · {feedback ? '已判题' : '材料闯关'}
          </Text>
          <CoinPill value={displayPoints} />
        </View>

        <Text className='quiz-progress'>
          第 {viewIndex + 1} 题 / 共 {total} 题
        </Text>
        <View className='quiz-progress-track'>
          <View className='quiz-progress-fill' style={{ width: `${progressPct}%` }} />
        </View>

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
                {feedback &&
                (question.answer_indexes.includes(idx) || selected.includes(idx)) ? (
                  <View className='dot'>
                    <Text className='dot-mark'>
                      {question.answer_indexes.includes(idx) ? '✓' : '✗'}
                    </Text>
                  </View>
                ) : null}
                <Text className='quiz-opt-label'>{opt}</Text>
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
                  <Text className='xp-gain'>
                    {isCorrectNow
                      ? `+${EXP_PER_CORRECT} EXP`
                      : `+${EXP_PER_WRONG} EXP（参与奖）`}
                  </Text>
                  <Text className='coin-gain'>
                    {isCorrectNow
                      ? `+${POINTS_PER_CORRECT} 积分`
                      : '积分无加成'}
                  </Text>
                </View>
                <Text className='gain-hint'>
                  本局累计 +{sessionPreview.expGained} EXP · +
                  {sessionPreview.pointsGained} 积分
                </Text>
              </View>
            </View>
            <View className={`feedback-sheet ${isCorrectNow ? 'ok' : 'bad'}`}>
              <View className='sheet-title-row'>
                <Text className='sheet-title'>知识讲解</Text>
                {question.explanation_source === 'ai' ||
                question.explanation?.startsWith('【AI 解析】') ? (
                  <Text className='source-badge ai'>AI</Text>
                ) : question.explanation &&
                  question.explanation !== '暂无解析' &&
                  !explainLoading ? (
                  <Text className='source-badge src'>原文</Text>
                ) : null}
              </View>
              <Text className='sheet-body'>
                {explainLoading && needsAiExplanation(question)
                  ? '正在生成解析…'
                  : question.explanation?.replace(/^【AI 解析】/, '') ||
                    '暂无解析'}
              </Text>
            </View>
          </>
        ) : null}

        <View className='quiz-scroll-spacer' />
      </ScrollView>

      {showFooter ? (
        <View className='quiz-footer'>
          {feedback ? (
            <View className='btn-row'>
              <View
                className={`btn secondary ${viewIndex === 0 ? 'disabled' : ''}`}
                onClick={goPrev}
              >
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
    </View>
  )
}
