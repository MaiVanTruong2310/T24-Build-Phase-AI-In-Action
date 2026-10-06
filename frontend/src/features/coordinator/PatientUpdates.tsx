import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react'
import { fetchWithAuth } from '../../app/apiClient'

interface Update { id: string; sender: string; body: string; created_at: string }

export interface SupportRequestState { busy: boolean; requested: boolean; control: string }
export interface PatientUpdatesHandle { requestHuman: () => void }

interface PatientUpdatesProps {
  sessionId: string
  owner: string
  canReply?: boolean
  showRequestButton?: boolean
  onSupportStateChange?: (state: SupportRequestState) => void
}

export const PatientUpdates = forwardRef<PatientUpdatesHandle, PatientUpdatesProps>(function PatientUpdates({
  sessionId,
  owner,
  canReply = false,
  showRequestButton = true,
  onSupportStateChange,
}, ref) {
  const [messages, setMessages] = useState<Update[]>([])
  const [control, setControl] = useState('ai')
  const [notice, setNotice] = useState('')
  const [reply, setReply] = useState('')
  const [busy, setBusy] = useState(false)
  const [humanRequested, setHumanRequested] = useState(false)
  const cursor = useRef('')
  const isPollingRef = useRef(false)

  useEffect(() => {
    let stopped = false
    let timer: ReturnType<typeof setTimeout> | undefined
    const controller = new AbortController()
    cursor.current = ''
    setMessages([])
    setControl('ai')
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

        const updates = (value.data?.messages || []) as Update[]
        const currentControl = value.data?.control || 'ai'
        const currentCase = value.data?.case

        setControl(currentControl)
        if (updates.length > 0) {
          setMessages(previous => [...previous, ...updates].filter((x, i, all) => all.findIndex(y => y.id === x.id) === i))
          cursor.current = updates[updates.length - 1].id
        }
        setNotice('')

        // Chỉ tiếp tục polling khi có ca điều phối thực sự cần theo dõi
        const isCaseActive = currentCase && currentCase.status !== 'observing' && currentCase.status !== 'completed' && currentCase.status !== 'cancelled'
        const shouldContinuePolling = canReply || humanRequested || currentControl === 'human' || updates.length > 0 || isCaseActive

        isPollingRef.current = Boolean(shouldContinuePolling)

        if (shouldContinuePolling && !stopped) {
          timer = setTimeout(poll, 5000)
        }
      } catch {
        if (!stopped && (canReply || humanRequested || isPollingRef.current)) {
          setNotice('Kết nối điều phối đang gián đoạn. Đang thử lại.')
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

  const requestHuman = async () => {
    if (busy || humanRequested || control === 'human') return
    setBusy(true)
    try {
      const response = await fetchWithAuth(`/coordination/live/${encodeURIComponent(sessionId)}/request-human`, { method: 'POST' })
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

  useImperativeHandle(ref, () => ({ requestHuman: () => { void requestHuman() } }))

  useEffect(() => {
    onSupportStateChange?.({ busy, requested: humanRequested, control })
  }, [busy, humanRequested, control, onSupportStateChange])

  const send = async () => {
    setBusy(true)
    try {
      const response = await fetchWithAuth(`/coordination/live/${encodeURIComponent(sessionId)}/messages`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ client_id: crypto.randomUUID(), body: reply }) })
      const value = await response.json()
      if (!response.ok) throw new Error(value.message || 'Không thể gửi tin nhắn.')
      setNotice(value.data.emergency_guidance || 'Đã gửi tin nhắn đến điều phối viên.'); setReply('')
    } catch (e) { setNotice(e instanceof Error ? e.message : 'Không thể gửi tin nhắn.') }
    finally { setBusy(false) }
  }

  return (
    <section className="mt-3 border-t border-slate-200 pt-3 text-xs text-slate-700">
      <div className="flex items-center justify-between gap-3">
        <strong>{control === 'human' ? 'Bác sĩ điều phối đang tiếp quản' : 'Hỗ trợ từ bác sĩ điều phối'}</strong>
        {showRequestButton && <button
          type="button"
          disabled={busy || humanRequested || control === 'human'}
          onClick={() => void requestHuman()}
          className="rounded border border-slate-300 bg-white px-3 py-2 disabled:opacity-60 transition-opacity"
        >
          {control === 'human' ? 'Đang kết nối bác sĩ' : humanRequested ? 'Đã gửi yêu cầu' : 'Yêu cầu hỗ trợ'}
        </button>}
      </div>
      {notice && <p role="status" className="mt-2 text-slate-600">{notice}</p>}
      {messages.map(m => (
        <article key={m.id} className="mt-3 rounded border border-slate-200 bg-white p-3">
          <div className="mb-2 flex justify-between gap-2 text-slate-500">
            <strong>{m.sender === 'coordinator' ? 'Bác sĩ điều phối' : 'Thông báo'}</strong>
            <time>{new Date(m.created_at).toLocaleString('vi-VN')}</time>
          </div>
          <p className="whitespace-pre-wrap">{m.body}</p>
        </article>
      ))}
      {canReply && (
        <form className="mt-4" onSubmit={e => { e.preventDefault(); void send() }}>
          <label className="block">
            Gửi thông tin bổ sung hoặc yêu cầu đổi/hủy
            <textarea required value={reply} onChange={e => setReply(e.target.value)} className="mt-2 block w-full rounded border border-slate-300 p-3" />
          </label>
          <button disabled={busy || !reply.trim()} className="mt-2 rounded border border-slate-300 bg-white px-3 py-2">
            {busy ? 'Đang gửi…' : 'Gửi tới điều phối viên'}
          </button>
        </form>
      )}
    </section>
  )
})
