import { useCallback, useEffect, useRef, useState } from 'react'
import { View, Text, Input } from '@tarojs/components'
import Taro, { useRouter } from '@tarojs/taro'
import {
  ApiError,
  confirmKnowledgeBaseMode,
  deleteKnowledgeBase,
  deleteKnowledgeDocument,
  fetchDrillStatus,
  fetchKnowledgeBases,
  fetchKnowledgeDocument,
  fetchKnowledgeDocuments,
  fetchMasterStatus,
  rebuildMasterMap,
  resetDrillPractice,
  resetMasterCoverage,
  updateKnowledgeBase,
  uploadKnowledgeDocument,
  type DrillStatusItem,
  type KnowledgeBaseItem,
  type KnowledgeBaseMode,
  type KnowledgeDocumentItem,
  type MasterStatusItem,
} from '../../utils/api'
import ConfirmModal from '../../components/ConfirmModal'
import { ensureLogin } from '../../utils/auth'
import { setPendingQuizStart } from '../../utils/pending'
import '../../styles/ui.scss'
import './detail.scss'

const POLL_MS = 3000
const COUNT_OPTIONS = [5, 10, 15, 20]

function statusLabel(status: KnowledgeDocumentItem['status']) {
  switch (status) {
    case 'ready':
      return '就绪'
    case 'failed':
      return '失败'
    case 'processing':
      return '入库中'
    case 'awaiting_mode':
      return '待确认模式'
    default:
      return '排队中'
  }
}

function modeLabel(mode?: KnowledgeBaseMode | null) {
  if (mode === 'drill') return '刷题'
  if (mode === 'master') return '学透'
  return '未确认'
}

async function waitUntilReady(kbId: number, docId: number) {
  const maxTries = 60
  for (let i = 0; i < maxTries; i += 1) {
    const doc = await fetchKnowledgeDocument(kbId, docId)
    if (doc.status === 'ready') return doc
    if (doc.status === 'failed') {
      throw new ApiError(
        'INGEST_FAILED',
        doc.error_message || '文档解析失败，请换一份再试',
      )
    }
    if (doc.status === 'awaiting_mode') {
      throw new ApiError('MODE_NOT_CONFIRMED', '请先确认知识库模式')
    }
    await new Promise((r) => setTimeout(r, 2000))
  }
  throw new ApiError('INGEST_TIMEOUT', '解析超时，请稍后再试')
}

export default function BankDetailPage() {
  const router = useRouter()
  const kbId = Number(router.params.id || 0)
  const [kb, setKb] = useState<KnowledgeBaseItem | null>(null)
  const [docs, setDocs] = useState<KnowledgeDocumentItem[]>([])
  const [drill, setDrill] = useState<DrillStatusItem | null>(null)
  const [master, setMaster] = useState<MasterStatusItem | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)
  const [starting, setStarting] = useState(false)
  const [confirmingMode, setConfirmingMode] = useState(false)
  const [nameDraft, setNameDraft] = useState('')
  const [savingName, setSavingName] = useState(false)
  const [questionCount, setQuestionCount] = useState(10)
  const [deleteKbOpen, setDeleteKbOpen] = useState(false)
  const [deletingKb, setDeletingKb] = useState(false)
  const [deleteDoc, setDeleteDoc] = useState<KnowledgeDocumentItem | null>(null)
  const [deletingDoc, setDeletingDoc] = useState(false)
  const [reviewOpen, setReviewOpen] = useState(false)
  const [masterReviewOpen, setMasterReviewOpen] = useState(false)
  const [masterDegradeOpen, setMasterDegradeOpen] = useState(false)
  const [resetting, setResetting] = useState(false)
  const [rebuildingMap, setRebuildingMap] = useState(false)
  const [changeModeOpen, setChangeModeOpen] = useState(false)
  const [pendingMode, setPendingMode] = useState<KnowledgeBaseMode | null>(null)
  const [emptyDrillOpen, setEmptyDrillOpen] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const autoSwitchToastRef = useRef(false)

  const refresh = useCallback(async () => {
    if (!kbId) {
      setError('无效的知识库')
      setLoading(false)
      return
    }
    try {
      await ensureLogin()
      const [bases, documents] = await Promise.all([
        fetchKnowledgeBases(),
        fetchKnowledgeDocuments(kbId),
      ])
      const found = bases.find((b) => b.id === kbId) || null
      setKb(found)
      setDocs(documents)
      if (found) {
        setNameDraft((prev) => (prev ? prev : found.name))
        setError('')
        Taro.setNavigationBarTitle({ title: found.name || '知识库' })
        try {
          const status = await fetchDrillStatus(kbId)
          setDrill(status)
          if (status.auto_switched_to_master && !autoSwitchToastRef.current) {
            autoSwitchToastRef.current = true
            Taro.showToast({
              title: '因未能拆题，已改为学透模式',
              icon: 'none',
              duration: 2500,
            })
          }
          if (status.needs_empty_drill_prompt) {
            setEmptyDrillOpen(true)
          } else {
            setEmptyDrillOpen(false)
          }
        } catch {
          setDrill(null)
        }
        if (found.mode === 'master') {
          try {
            setMaster(await fetchMasterStatus(kbId))
          } catch {
            setMaster(null)
          }
        } else {
          setMaster(null)
        }
      } else {
        setError('知识库不存在')
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }, [kbId])

  useEffect(() => {
    refresh()
  }, [refresh])

  useEffect(() => {
    const needPoll =
      docs.some((d) => d.status === 'pending' || d.status === 'processing') ||
      master?.map_status === 'pending'
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
    if (!needPoll) return
    pollRef.current = setInterval(() => {
      void refresh()
    }, POLL_MS)
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [docs, master?.map_status, refresh])

  const onSaveName = async () => {
    const name = nameDraft.trim()
    if (!name || !kb || name === kb.name || savingName) return
    try {
      setSavingName(true)
      const updated = await updateKnowledgeBase(kbId, { name })
      setKb(updated)
      setNameDraft(updated.name)
      Taro.setNavigationBarTitle({ title: updated.name })
      Taro.showToast({ title: '名称已更新', icon: 'success' })
    } catch (err) {
      Taro.showToast({
        title: err instanceof ApiError ? err.message : '改名失败',
        icon: 'none',
      })
      setNameDraft(kb.name)
    } finally {
      setSavingName(false)
    }
  }

  const onConfirmMode = async (mode: KnowledgeBaseMode) => {
    if (confirmingMode || starting) return
    try {
      setConfirmingMode(true)
      const updated = await confirmKnowledgeBaseMode(kbId, mode, true)
      setKb(updated)
      setChangeModeOpen(false)
      setPendingMode(null)
      setEmptyDrillOpen(false)
      Taro.showToast({
        title:
          mode === 'drill'
            ? '已切换为刷题，正在重新处理文档'
            : '已切换为学透，正在重新处理文档',
        icon: 'none',
      })
      await refresh()
    } catch (err) {
      Taro.showToast({
        title: err instanceof ApiError ? err.message : '确认失败',
        icon: 'none',
      })
    } finally {
      setConfirmingMode(false)
    }
  }

  const askChangeMode = (mode: KnowledgeBaseMode) => {
    if (!kb?.mode || kb.mode === mode || confirmingMode) return
    setPendingMode(mode)
    setChangeModeOpen(true)
  }

  const onUpload = async () => {
    if (uploading || starting) return
    try {
      setUploading(true)
      const chosen = await Taro.chooseMessageFile({
        count: 1,
        type: 'file',
        extension: ['pdf', 'docx', 'md', 'markdown'],
      })
      const file = chosen.tempFiles?.[0]
      if (!file) return
      await uploadKnowledgeDocument(kbId, file.path, file.name)
      // Keep KB title in sync with the current (or replaced) file name.
      if (file.name) {
        const stem = file.name.replace(/\.[^.]+$/, '') || file.name
        try {
          const updated = await updateKnowledgeBase(kbId, { name: stem.slice(0, 64) })
          setKb(updated)
          setNameDraft(updated.name)
          Taro.setNavigationBarTitle({ title: updated.name })
        } catch {
          setNameDraft(stem.slice(0, 64))
        }
      }
      Taro.showToast({
        title: docs.length ? '已替换，正在解析' : '已上传，正在解析',
        icon: 'none',
      })
      await refresh()
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? err.message
          : typeof err === 'object' && err && 'errMsg' in err
            ? String((err as { errMsg?: string }).errMsg || '已取消')
            : '上传失败'
      if (!/cancel|取消/i.test(msg)) {
        Taro.showToast({ title: msg.slice(0, 40), icon: 'none' })
      }
    } finally {
      setUploading(false)
    }
  }

  const confirmDeleteDoc = async () => {
    if (!deleteDoc || deletingDoc) return
    try {
      setDeletingDoc(true)
      await deleteKnowledgeDocument(kbId, deleteDoc.id)
      setDeleteDoc(null)
      Taro.showToast({ title: '已删除', icon: 'success' })
      await refresh()
    } catch (err) {
      Taro.showToast({
        title: err instanceof ApiError ? err.message : '删除失败',
        icon: 'none',
      })
    } finally {
      setDeletingDoc(false)
    }
  }

  const confirmDeleteKb = async () => {
    if (deletingKb) return
    try {
      setDeletingKb(true)
      await deleteKnowledgeBase(kbId)
      setDeleteKbOpen(false)
      Taro.showToast({ title: '已删除', icon: 'success' })
      Taro.navigateBack()
    } catch (err) {
      Taro.showToast({
        title: err instanceof ApiError ? err.message : '删除失败',
        icon: 'none',
      })
    } finally {
      setDeletingKb(false)
    }
  }

  const launchQuiz = async (opts?: { drill_round?: 'review' }) => {
    const name = nameDraft.trim() || kb?.name || '未命名'
    if (kb && name !== kb.name) {
      await updateKnowledgeBase(kbId, { name })
    }

    let readyDocs = docs.filter((d) => d.status === 'ready')
    const pending = docs.filter(
      (d) => d.status === 'pending' || d.status === 'processing',
    )
    if (!readyDocs.length && pending.length) {
      Taro.showLoading({ title: '等待解析完成…', mask: true })
      await waitUntilReady(kbId, pending[0].id)
      Taro.hideLoading()
      await refresh()
      const latest = await fetchKnowledgeDocuments(kbId)
      readyDocs = latest.filter((d) => d.status === 'ready')
    }
    if (!readyDocs.length && kb?.mode !== 'drill') {
      Taro.showToast({
        title: '请先上传并等待文档就绪',
        icon: 'none',
      })
      return
    }

    setPendingQuizStart({
      source_text: `根据知识库「${name}」的资料出题闯关`,
      knowledge_base_id: kbId,
      topic_name: name,
      question_count: questionCount,
      drill_round: opts?.drill_round,
    })
    Taro.navigateTo({ url: '/pages/generate/index' })
  }

  const onStartQuiz = async () => {
    if (starting || uploading || confirmingMode) return
    if (!kb?.mode || !kb.mode_confirmed_at) {
      Taro.showToast({ title: '请先确认刷题或学透模式', icon: 'none' })
      return
    }
    try {
      setStarting(true)
      if (kb.mode === 'drill') {
        const status = drill || (await fetchDrillStatus(kbId))
        setDrill(status)
        if (status.warning) {
          Taro.showToast({ title: status.warning.slice(0, 40), icon: 'none' })
        }
        if (status.needs_empty_drill_prompt) {
          setEmptyDrillOpen(true)
          return
        }
        if (status.total_questions < 1) {
          Taro.showToast({
            title: docs.length ? '请等待文档解析完成' : '请先上传题库文档',
            icon: 'none',
          })
          return
        }
        if (status.needs_review_prompt) {
          setReviewOpen(true)
          return
        }
      } else if (kb.mode === 'master') {
        const status = master || (await fetchMasterStatus(kbId))
        setMaster(status)
        if (status.needs_review_prompt) {
          setMasterReviewOpen(true)
          return
        }
        if (status.map_status === 'pending' || status.map_status === 'failed') {
          setMasterDegradeOpen(true)
          return
        }
      }
      await launchQuiz()
    } catch (err) {
      Taro.hideLoading()
      const code = err instanceof ApiError ? err.error_code : ''
      const msg =
        code === 'MODE_NOT_CONFIRMED'
          ? '请先确认知识库模式'
          : code === 'DRILL_EMPTY'
            ? '刷题库没有可用题'
            : code === 'MASTER_NEEDS_REVIEW'
              ? '要点已过一轮，请复习或重置'
              : err instanceof ApiError
                ? err.message.slice(0, 40)
                : '无法开局'
      Taro.showToast({ title: msg, icon: 'none' })
    } finally {
      setStarting(false)
    }
  }

  const onReviewRound = async () => {
    setReviewOpen(false)
    setMasterReviewOpen(false)
    try {
      setStarting(true)
      await launchQuiz({ drill_round: 'review' })
    } catch (err) {
      Taro.showToast({
        title: err instanceof ApiError ? err.message.slice(0, 40) : '无法开局',
        icon: 'none',
      })
    } finally {
      setStarting(false)
    }
  }

  const onResetPractice = async () => {
    if (resetting) return
    try {
      setResetting(true)
      await resetDrillPractice(kbId)
      setReviewOpen(false)
      Taro.showToast({ title: '已重置刷题进度', icon: 'success' })
      await refresh()
      setStarting(true)
      await launchQuiz()
    } catch (err) {
      Taro.showToast({
        title: err instanceof ApiError ? err.message : '重置失败',
        icon: 'none',
      })
    } finally {
      setResetting(false)
      setStarting(false)
    }
  }

  const onResetMasterCoverage = async () => {
    if (resetting) return
    try {
      setResetting(true)
      await resetMasterCoverage(kbId)
      setMasterReviewOpen(false)
      Taro.showToast({ title: '已重置学透覆盖', icon: 'success' })
      await refresh()
      setStarting(true)
      await launchQuiz()
    } catch (err) {
      Taro.showToast({
        title: err instanceof ApiError ? err.message : '重置失败',
        icon: 'none',
      })
    } finally {
      setResetting(false)
      setStarting(false)
    }
  }

  const onRebuildMasterMap = async () => {
    if (rebuildingMap) return
    try {
      setRebuildingMap(true)
      const status = await rebuildMasterMap(kbId)
      setMaster(status)
      Taro.showToast({ title: '已开始重建要点地图', icon: 'none' })
      await refresh()
    } catch (err) {
      Taro.showToast({
        title: err instanceof ApiError ? err.message.slice(0, 40) : '重建失败',
        icon: 'none',
      })
    } finally {
      setRebuildingMap(false)
    }
  }

  const onConfirmMasterDegrade = async () => {
    setMasterDegradeOpen(false)
    try {
      setStarting(true)
      await launchQuiz()
    } catch (err) {
      Taro.showToast({
        title: err instanceof ApiError ? err.message.slice(0, 40) : '无法开局',
        icon: 'none',
      })
    } finally {
      setStarting(false)
    }
  }

  const modeConfirmed = Boolean(kb?.mode && kb.mode_confirmed_at)
  const suggested = kb?.suggested_mode || drill?.suggested_mode
  const isDrill = kb?.mode === 'drill'
  const isMaster = kb?.mode === 'master'

  if (loading) {
    return (
      <View className='page-shell'>
        <Text className='hint'>加载中…</Text>
      </View>
    )
  }

  return (
    <View className='page-shell'>
      <View className='page-body bank-detail-body'>
        <View className='name-field'>
          <Text className='field-label'>主题名</Text>
          <Input
            className='name-input'
            value={nameDraft}
            maxlength={64}
            disabled={savingName || starting}
            onInput={(e) => setNameDraft(e.detail.value)}
            onBlur={() => void onSaveName()}
            onConfirm={() => void onSaveName()}
          />
        </View>

        <View className='mode-panel'>
          <View className='mode-row'>
            <Text className='mode-badge'>
              当前模式：{modeLabel(kb?.mode)}
            </Text>
            {modeConfirmed ? (
              <Text
                className='link-change'
                onClick={() =>
                  askChangeMode(isDrill ? 'master' : 'drill')
                }
              >
                更改模式
              </Text>
            ) : null}
          </View>
          {!modeConfirmed ? (
            <>
              <Text className='mode-hint'>
                {suggested
                  ? `系统建议：${modeLabel(suggested)}（可改选）`
                  : '上传文档后会给出模式建议，也可先选定再入库'}
              </Text>
              <View className='mode-actions'>
                <View
                  className={`btn secondary mode-btn ${confirmingMode ? 'disabled' : ''}`}
                  onClick={() => {
                    if (!confirmingMode) void onConfirmMode('drill')
                  }}
                >
                  刷题（抽原题）
                </View>
                <View
                  className={`btn mode-btn ${confirmingMode ? 'disabled' : ''}`}
                  onClick={() => {
                    if (!confirmingMode) void onConfirmMode('master')
                  }}
                >
                  学透（AI 出题）
                </View>
              </View>
            </>
          ) : isDrill && drill ? (
            <Text className='mode-hint'>
              题库 {drill.total_questions} 题 · 未刷 {drill.unseen_questions}
            </Text>
          ) : isMaster && master ? (
            <View className='master-progress'>
              <Text className='mode-hint'>
                {master.map_status === 'ready'
                  ? `要点已覆盖 ${master.covered_points} / 共 ${master.total_points}`
                  : master.map_status === 'pending'
                    ? '要点地图生成中…'
                    : master.map_status === 'failed'
                      ? '要点地图生成失败'
                      : '学透模式：按要点覆盖出题'}
              </Text>
              {master.warning ? (
                <Text className='hint warn'>{master.warning}</Text>
              ) : null}
              {master.map_status === 'failed' || master.map_status === 'pending' ? (
                <Text
                  className={`link-change ${rebuildingMap ? 'disabled' : ''}`}
                  onClick={() => {
                    if (!rebuildingMap) void onRebuildMasterMap()
                  }}
                >
                  {rebuildingMap ? '重建中…' : '重建要点地图'}
                </Text>
              ) : null}
            </View>
          ) : (
            <Text className='mode-hint'>学透模式：按要点覆盖出题</Text>
          )}
        </View>

        {drill?.needs_empty_drill_prompt ? (
          <View className='empty-drill-banner'>
            <Text className='empty-drill-title'>刷题拆题失败</Text>
            <Text className='empty-drill-msg'>
              {drill?.warning ||
                '未能识别题目。可改为学透用资料出题，或重新上传规范题库。'}
            </Text>
            <View className='mode-actions'>
              <View
                className={`btn secondary mode-btn ${confirmingMode || uploading ? 'disabled' : ''}`}
                onClick={() => {
                  if (!uploading) void onUpload()
                }}
              >
                替换文档
              </View>
              <View
                className={`btn mode-btn ${confirmingMode ? 'disabled' : ''}`}
                onClick={() => {
                  if (!confirmingMode) void onConfirmMode('master')
                }}
              >
                改为学透
              </View>
            </View>
          </View>
        ) : null}

        {error ? <Text className='hint warn'>{error}</Text> : null}

        <View
          className={`upload-drop ${uploading ? 'active' : ''}`}
          onClick={() => void onUpload()}
        >
          <View className='upload-glyph'>文</View>
          <Text className='upload-title'>
            {uploading
              ? '上传中…'
              : docs.length
                ? '替换当前文档'
                : '把 PDF / Word / MD 丢进来'}
          </Text>
          <Text className='upload-sub'>
            {docs.length
              ? '每个知识库只保留一份材料，再选文件会覆盖旧的'
              : '从微信聊天记录选择文件上传'}
          </Text>
        </View>

        {docs.map((doc) => (
          <View key={doc.id} className='list-item'>
            <View className='meta'>
              <Text className='meta-title'>{doc.filename}</Text>
              <Text className='meta-sub'>
                {statusLabel(doc.status)}
                {doc.status === 'ready'
                  ? isDrill
                    ? ` · ${doc.chunk_count} 题`
                    : ` · ${doc.chunk_count} 片段`
                  : ''}
                {doc.error_message ? ` · ${doc.error_message}` : ''}
              </Text>
            </View>
            <Text className='link-danger' onClick={() => setDeleteDoc(doc)}>
              删除
            </Text>
          </View>
        ))}

        {!docs.length ? (
          <View className='comic-panel'>
            <Text className='hint'>还没有文档，先点上方虚线框上传一份。</Text>
          </View>
        ) : null}

        {modeConfirmed ? (
          <View className='count-row'>
            <Text className='field-label'>本局题量</Text>
            <View className='count-chips'>
              {COUNT_OPTIONS.map((n) => (
                <View
                  key={n}
                  className={`count-chip ${questionCount === n ? 'on' : ''}`}
                  onClick={() => setQuestionCount(n)}
                >
                  <Text>{n}</Text>
                </View>
              ))}
            </View>
          </View>
        ) : null}

        <View
          className={`btn ${starting || !modeConfirmed ? 'disabled' : ''}`}
          onClick={() => {
            if (!starting && modeConfirmed) void onStartQuiz()
          }}
        >
          {starting
            ? '准备中…'
            : !modeConfirmed
              ? '请先确认模式'
              : isDrill
                ? '开始刷题'
                : '开始闯关'}
        </View>
        <View className='btn ghost' onClick={() => setDeleteKbOpen(true)}>
          删除整个知识库
        </View>
      </View>

      <ConfirmModal
        open={deleteKbOpen}
        mood='sweat'
        title='要删掉整个知识库吗？'
        message='库内文档和向量都会清掉，删了就找不回来了。'
        cancelText='再想想'
        confirmText={deletingKb ? '删除中…' : '确定删除'}
        onCancel={() => {
          if (!deletingKb) setDeleteKbOpen(false)
        }}
        onConfirm={() => {
          if (!deletingKb) void confirmDeleteKb()
        }}
      />

      <ConfirmModal
        open={!!deleteDoc}
        mood='think'
        title='要删除这份文档吗？'
        message={
          deleteDoc
            ? `「${deleteDoc.filename}」删了就没了，对应向量也会一起清掉。`
            : ''
        }
        cancelText='再想想'
        confirmText={deletingDoc ? '删除中…' : '确定删除'}
        onCancel={() => {
          if (!deletingDoc) setDeleteDoc(null)
        }}
        onConfirm={() => {
          if (!deletingDoc) void confirmDeleteDoc()
        }}
      />

      <ConfirmModal
        open={reviewOpen}
        mood='cheer'
        title='本库题目已刷完一遍'
        message='可以进入复习轮，或重置进度后重新抽未刷题。'
        cancelText='取消'
        extraText={resetting ? '重置中…' : '重置进度'}
        confirmText='开始复习轮'
        onCancel={() => {
          if (!resetting && !starting) setReviewOpen(false)
        }}
        onExtra={() => {
          if (!resetting) void onResetPractice()
        }}
        onConfirm={() => {
          if (!starting) void onReviewRound()
        }}
      />

      <ConfirmModal
        open={masterReviewOpen}
        mood='cheer'
        title='本库要点已过一轮'
        message='可以进入复习轮（优先久远要点），或重置覆盖后重新学透。'
        cancelText='取消'
        extraText={resetting ? '重置中…' : '重置覆盖'}
        confirmText='开始复习轮'
        onCancel={() => {
          if (!resetting && !starting) setMasterReviewOpen(false)
        }}
        onExtra={() => {
          if (!resetting) void onResetMasterCoverage()
        }}
        onConfirm={() => {
          if (!starting) void onReviewRound()
        }}
      />

      <ConfirmModal
        open={masterDegradeOpen}
        mood='think'
        title={
          master?.map_status === 'failed'
            ? '要点地图未就绪'
            : '要点地图生成中'
        }
        message={
          master?.map_status === 'failed'
            ? '可先用旧检索开局（非覆盖学透），或先重建地图。'
            : '可先用旧检索开局（非覆盖学透），地图就绪后会按未覆盖要点出题。'
        }
        cancelText='取消'
        extraText={rebuildingMap ? '重建中…' : '重建地图'}
        confirmText='仍要开局'
        onCancel={() => {
          if (!starting && !rebuildingMap) setMasterDegradeOpen(false)
        }}
        onExtra={() => {
          if (!rebuildingMap) void onRebuildMasterMap()
        }}
        onConfirm={() => {
          if (!starting) void onConfirmMasterDegrade()
        }}
      />

      <ConfirmModal
        open={changeModeOpen}
        mood='think'
        title={
          pendingMode === 'master'
            ? '改为学透模式？'
            : '改为刷题模式？'
        }
        message={
          pendingMode === 'master'
            ? '将清空刷题进度与已拆题目，文档会按学透重新向量入库。'
            : '文档将按刷题重新拆题入库；学透要点地图与覆盖进度会一并清除。'
        }
        cancelText='取消'
        confirmText={confirmingMode ? '切换中…' : '确定更改'}
        onCancel={() => {
          if (!confirmingMode) {
            setChangeModeOpen(false)
            setPendingMode(null)
          }
        }}
        onConfirm={() => {
          if (pendingMode && !confirmingMode) void onConfirmMode(pendingMode)
        }}
      />

      <ConfirmModal
        open={emptyDrillOpen && !drill?.needs_empty_drill_prompt}
        mood='sweat'
        title='刷题库暂无可用题'
        message='未能拆出文本题。可改为学透，或换一份规范题库文档。'
        cancelText='先看看'
        confirmText='改为学透'
        onCancel={() => setEmptyDrillOpen(false)}
        onConfirm={() => {
          if (!confirmingMode) void onConfirmMode('master')
        }}
      />
    </View>
  )
}
