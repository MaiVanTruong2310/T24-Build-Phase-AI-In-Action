import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react'
import { AlertCircle, Headset, LoaderCircle, Send, Stethoscope, UserCheck } from 'lucide-react'
import { fetchWithAuth } from '../../app/apiClient'

export interface Update {
  id: string
  sender: 'coordinator' | 'patient' | 'system' | string
  body: string
  created_at: string
}

export interface SupportRequestState {
  busy: boolean
  requested: boolean
  control: string
}

export interface PatientUpdatesHandle {
  requestHuman: () => void
  sendMessage: (body: string) => Promise<void>
}

interface PatientUpdatesProps {
  sessionId: string
  owner: string
  canReply?: boolean
  showRequestButton?: boolean
  mode?: 'standalone' | 'embedded'
  onSupportStateChange?: (state: SupportRequestState) => void
  onCoordinatorMessages?: (messages: Update[]) => void
}

export const PatientUpdates = forwardRef<PatientUpdatesHandle, PatientUpdatesProps>(function PatientUpdates(
  {
    sessionId,
    owner,
    canReply = false,
    showRequestButton = true,
    mode = 'standalone',
    onSupportStateChange,
    onCoordinatorMessages,
  },
  ref
) {
  const [messages, setMessages] = useState<Update[]>([])
  const [control, setControl] = useState('ai')
  const [caseStatus, setCaseStatus] = useState('observing')
  const [notice, setNotice] = useState('')
  const [reply, setReply] = useState('')
  const [busy, setBusy] = useState(false)
  const [humanRequested, setHumanRequested] = useState(false)
  const cursor = useRef('')
  const isPollingRef = useRef(false)
  const scrollAnchorRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let stopped = false
    let timer: ReturnType<typeof setTimeout> | undefined
    const controller = new AbortController()
    cursor.current = ''
    setMessages([])
    setControl('ai')
    setCaseStatus('observing')
    setNotice('')
    setHumanRequested(false)

    const poll = async () => {
      if (document.hidden) {
        if (!stopped && (canReply || humanRequested || isPollingRef.current)) {
          timer = setTimeout(poll, 5000)
        }
        return
      }

      try {
        const response = await fetchWithAuth(
          `/coordination/live/${encodeURIComponent(sessionId)}${cursor.current ? '?after=' + cursor.current : ''}`,
          { signal: controller.signal }
        )
        const value = await response.json()
        if (!response.ok) throw new Error(value.message || 'Chưa kết nối được với điều phối viên.')
        if (stopped) return

        const rawUpdates = (value.data?.messages || []) as Update[]
        // Phòng ngừa hai lớp: Loại trừ mọi tin nhắn xuất phát từ bot hoặc assistant
        const updates = rawUpdates.filter(
          (u) => u.sender !== 'ai' && u.sender !== 'assistant' && u.sender !== 'agent'
        )
        const currentControl = value.data?.control || 'ai'
        const currentCase = value.data?.case

        setControl(currentControl)
        if (currentCase?.status) {
          setCaseStatus(currentCase.status)
        }
        if (updates.length > 0) {
          setMessages((previous) =>
            [...previous, ...updates].filter(
              (x, i, all) => all.findIndex((y) => y.id === x.id) === i
            )
          )
          cursor.current = updates[updates.length - 1].id
          onCoordinatorMessages?.(updates)
        }
        setNotice('')

        // Chỉ tiếp tục polling khi có ca điều phối thực sự cần theo dõi
        const isCaseActive =
          currentCase &&
          currentCase.status !== 'observing' &&
          currentCase.status !== 'completed' &&
          currentCase.status !== 'cancelled'
        const shouldContinuePolling =
          canReply || humanRequested || currentControl === 'human' || updates.length > 0 || isCaseActive

        isPollingRef.current = Boolean(shouldContinuePolling)

        if (shouldContinuePolling && !stopped) {
          timer = setTimeout(poll, 4000)
        }
      } catch {
        if (!stopped && (canReply || humanRequested || isPollingRef.current)) {
          setNotice('Kết nối điều phối đang gián đoạn. Đang tự động thử lại…')
          timer = setTimeout(poll, 8000)
        }
      }
    }

    void poll()

    return () => {
      stopped = true
      if (timer) clearTimeout(timer)
      controller.abort()
    }
  }, [sessionId, owner, canReply, humanRequested])

  // Tự động cuộn xuống khi có tin nhắn mới trong phiên
  useEffect(() => {
    if (messages.length > 0) {
      scrollAnchorRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages.length])

  const requestHuman = async () => {
    if (busy || humanRequested || control === 'human') return
    setBusy(true)
    try {
      const response = await fetchWithAuth(
        `/coordination/live/${encodeURIComponent(sessionId)}/request-human`,
        { method: 'POST' }
      )
      const value = await response.json()
      if (response.ok) {
        setNotice('Đã gửi yêu cầu hỗ trợ đến bác sĩ điều phối.')
        setHumanRequested(true)
      } else {
        setNotice(value.message || 'Không thể gửi yêu cầu.')
      }
    } catch {
      setNotice('Không thể gửi yêu cầu. Vui lòng thử lại.')
    } finally {
      setBusy(false)
    }
  }

  const sendText = async (rawText: string) => {
    const trimmed = rawText.trim()
    if (!trimmed || busy) return

    setBusy(true)
    const tempId = `temp-${Date.now()}`
    // Thêm tin nhắn tạm vào danh sách ngay lập tức để tạo cảm giác mượt mà (Optimistic UI)
    const optimisticMsg: Update = {
      id: tempId,
      sender: 'patient',
      body: trimmed,
      created_at: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, optimisticMsg])
    setReply('')

    try {
      const response = await fetchWithAuth(
        `/coordination/live/${encodeURIComponent(sessionId)}/messages`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ client_id: crypto.randomUUID(), body: trimmed }),
        }
      )
      const value = await response.json()
      if (!response.ok) throw new Error(value.message || 'Không thể gửi tin nhắn.')
      if (value.data?.emergency_guidance) {
        setNotice(value.data.emergency_guidance)
      }
    } catch (e) {
      setNotice(e instanceof Error ? e.message : 'Không thể gửi tin nhắn.')
      // Hoàn tác tin nhắn tạm nếu gửi thất bại
      setMessages((prev) => prev.filter((m) => m.id !== tempId))
      setReply(trimmed)
      throw e
    } finally {
      setBusy(false)
    }
  }

  useImperativeHandle(ref, () => ({
    requestHuman: () => {
      void requestHuman()
    },
    sendMessage: async (body: string) => {
      await sendText(body)
    },
  }))

  useEffect(() => {
    onSupportStateChange?.({ busy, requested: humanRequested, control })
  }, [busy, humanRequested, control, onSupportStateChange])

  // Trong embedded mode (tích hợp trong ChatbotWidget):
  // Toàn bộ trải nghiệm điều phối viên diễn ra ngay trong luồng chat chính (giống nhóm chat Messenger)
  // Không render khung chat con thứ hai để tránh lặp 2 ô input và vỡ giao diện
  if (mode === 'embedded') {
    return null
  }

  // Phiên điều phối CHỈ kích hoạt khi:
  // 1. Người dùng chủ động bấm yêu cầu hỗ trợ (humanRequested)
  // 2. Bác sĩ điều phối đang trực tuyến tiếp quản (control === 'human')
  // 3. Thực sự có tin nhắn từ Bác sĩ điều phối gửi cho bệnh nhân (hasCoordinatorMessages)
  // 4. Ca điều phối đang ở trạng thái active (đã được tiếp nhận/chuyển ca/khẩn cấp, không phải chỉ quan sát ngầm)
  const hasCoordinatorMessages = messages.some((m) => m.sender === 'coordinator')
  const isCaseActive = Boolean(
    caseStatus &&
      caseStatus !== 'observing' &&
      caseStatus !== 'completed' &&
      caseStatus !== 'cancelled'
  )
  const isSessionActive = humanRequested || control === 'human' || hasCoordinatorMessages || isCaseActive
  if (!isSessionActive && !showRequestButton && !canReply) {
    return null
  }

  const isHumanActive = control === 'human'
  const allowReplying = canReply || isHumanActive || humanRequested

  return (
    <section
      aria-label="Phiên kết nối điều phối viên y tế"
      className="mt-3 rounded-2xl border border-emerald-500/20 bg-gradient-to-b from-emerald-50/60 to-white dark:from-emerald-950/20 dark:to-[#0B1329] p-3 text-xs shadow-sm transition-all"
    >
      {/* ─── Header phiên điều phối ─── */}
      <div className="flex items-center justify-between gap-2 border-b border-emerald-500/15 pb-2.5 dark:border-emerald-500/20">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-emerald-100 text-[#176a52] dark:bg-emerald-900/50 dark:text-emerald-300 ring-2 ring-emerald-500/20">
            {isHumanActive ? (
              <UserCheck className="h-4 w-4" />
            ) : (
              <Stethoscope className="h-4 w-4" />
            )}
          </div>
          <div>
            <div className="flex items-center gap-1.5 font-semibold text-slate-800 dark:text-slate-100 text-[12px]">
              <span>Phiên hỗ trợ điều phối viên</span>
              {isHumanActive && (
                <span className="rounded-full bg-emerald-100 dark:bg-emerald-900/60 px-1.5 py-0.2 text-[9px] font-bold text-emerald-800 dark:text-emerald-200">
                  Trực tuyến
                </span>
              )}
            </div>
            <div className="flex items-center gap-1.5 text-[10px] text-slate-500 dark:text-slate-400">
              {isHumanActive ? (
                <>
                  <span className="relative flex h-2 w-2">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
                  </span>
                  <span className="font-medium text-emerald-700 dark:text-emerald-300">
                    Bác sĩ điều phối đang trực tiếp hỗ trợ
                  </span>
                </>
              ) : humanRequested ? (
                <>
                  <span className="relative flex h-2 w-2">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400 opacity-75"></span>
                    <span className="relative inline-flex h-2 w-2 rounded-full bg-amber-500"></span>
                  </span>
                  <span className="font-medium text-amber-700 dark:text-amber-400">
                    Đang chờ bác sĩ điều phối nhận phiên…
                  </span>
                </>
              ) : (
                <span>Kênh trao đổi riêng với Bác sĩ điều phối</span>
              )}
            </div>
          </div>
        </div>

        {showRequestButton && (
          <button
            type="button"
            disabled={busy || humanRequested || isHumanActive}
            onClick={() => void requestHuman()}
            className="inline-flex items-center gap-1.5 rounded-xl border border-emerald-600 bg-white dark:bg-slate-800 px-3 py-1.5 text-[11px] font-medium text-emerald-700 dark:text-emerald-300 hover:bg-emerald-50 dark:hover:bg-slate-700 disabled:opacity-50 transition-all cursor-pointer shadow-2xs"
          >
            <Headset className="h-3.5 w-3.5" />
            <span>
              {isHumanActive
                ? 'Đã kết nối'
                : humanRequested
                ? 'Đã gửi yêu cầu'
                : 'Yêu cầu hỗ trợ'}
            </span>
          </button>
        )}
      </div>

      {/* ─── Thông báo trạng thái / lỗi ─── */}
      {notice && (
        <div
          role="status"
          className="mt-2.5 flex items-start gap-1.5 rounded-xl border border-amber-200 dark:border-amber-900/50 bg-amber-50/90 dark:bg-amber-950/40 p-2 text-[11px] text-amber-800 dark:text-amber-300"
        >
          <AlertCircle className="h-3.5 w-3.5 shrink-0 mt-0.5 text-amber-600 dark:text-amber-400" />
          <span>{notice}</span>
        </div>
      )}

      {/* ─── Luồng tin nhắn nhóm chat theo phiên ─── */}
      <div className="mt-2.5 max-h-72 space-y-2.5 overflow-y-auto pr-1 text-xs">
        {messages.length === 0 && (
          <div className="py-4 text-center text-[11px] text-slate-400 dark:text-slate-500">
            {humanRequested
              ? 'Yêu cầu của bạn đã được ghi nhận. Bác sĩ điều phối sẽ sớm nhắn lại trong khung này.'
              : 'Chưa có tin nhắn trong phiên điều phối.'}
          </div>
        )}

        {messages.map((m) => {
          const isCoordinator = m.sender === 'coordinator'
          const isPatient = m.sender === 'patient'

          if (isCoordinator) {
            return (
              <div key={m.id} className="flex items-start gap-2">
                <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-100 dark:bg-emerald-900/60 text-emerald-700 dark:text-emerald-300 ring-1 ring-emerald-500/20 text-[10px] font-bold">
                  BS
                </div>
                <div className="max-w-[85%]">
                  <div className="mb-0.5 flex items-center gap-1.5 text-[10px]">
                    <span className="font-semibold text-emerald-800 dark:text-emerald-300">
                      Bác sĩ điều phối
                    </span>
                    <time className="font-mono text-slate-400 dark:text-slate-500 text-[9px]">
                      {new Date(m.created_at).toLocaleTimeString('vi-VN', {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </time>
                  </div>
                  <div className="rounded-2xl rounded-tl-xs border border-emerald-200/90 bg-white p-2.5 text-slate-800 shadow-2xs dark:border-emerald-800/80 dark:bg-[#0c1830] dark:text-slate-100 whitespace-pre-wrap leading-relaxed">
                    {m.body}
                  </div>
                </div>
              </div>
            )
          }

          if (isPatient) {
            return (
              <div key={m.id} className="flex justify-end items-start gap-2">
                <div className="max-w-[85%] text-right">
                  <div className="mb-0.5 text-[9px] font-mono text-slate-400 dark:text-slate-500">
                    {new Date(m.created_at).toLocaleTimeString('vi-VN', {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </div>
                  <div className="rounded-2xl rounded-tr-xs bg-gradient-to-r from-[#176a52] to-[#125844] p-2.5 text-left text-white shadow-2xs whitespace-pre-wrap leading-relaxed">
                    {m.body}
                  </div>
                </div>
              </div>
            )
          }

          // Sự kiện hệ thống (system event / deposit / booking update)
          return (
            <div key={m.id} className="my-1.5 flex justify-center">
              <div className="inline-flex items-center gap-1 rounded-full border border-slate-200 dark:border-slate-800 bg-slate-100/90 dark:bg-slate-800/90 px-3 py-1 text-[10px] text-slate-600 dark:text-slate-300 text-center">
                <span>{m.body}</span>
              </div>
            </div>
          )
        })}
        <div ref={scrollAnchorRef} />
      </div>

      {/* ─── Thanh gõ tin nhắn phản hồi cho điều phối viên ─── */}
      {allowReplying && (
        <form
          className="mt-3 flex items-center gap-1.5"
          onSubmit={(e) => {
            e.preventDefault()
            void sendText(reply)
          }}
        >
          <input
            type="text"
            required
            value={reply}
            disabled={busy}
            onChange={(e) => setReply(e.target.value)}
            placeholder="Nhắn tin cho Bác sĩ điều phối…"
            aria-label="Nội dung nhắn tin cho bác sĩ điều phối"
            className="flex-1 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-[#0c1830] px-3 py-2 text-xs text-slate-800 dark:text-slate-100 placeholder:text-slate-400 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
          />
          <button
            type="submit"
            disabled={busy || !reply.trim()}
            aria-label="Gửi tin nhắn"
            className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-gradient-to-r from-[#176a52] to-[#125844] text-white shadow-2xs hover:from-[#1b795e] hover:to-[#15634d] disabled:opacity-50 transition-all cursor-pointer"
          >
            {busy ? (
              <LoaderCircle className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Send className="h-3.5 w-3.5" />
            )}
          </button>
        </form>
      )}
    </section>
  )
})
