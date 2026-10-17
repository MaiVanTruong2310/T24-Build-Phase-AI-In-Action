import { Bot, MessageSquareText, Send, X } from 'lucide-react'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { resolveStaffWorkbenchWebSocketUrl } from '../coordinator/api'
import { fetchTakeoverTicket } from '../chat/api'
import { websocketNeedsTicket } from '../../app/apiClient'
import { useDispatch } from 'react-redux'
import type { AppDispatch } from '../../app/store'
import { clearBookingApprovalPages } from '../booking-approvals/bookingApprovalsSlice'
import { cancelStaffAction, confirmStaffAction, fetchStaffAssistantAlerts, sendStaffMessageStream, type PendingAction, type StaffAssistantAlert } from './api'

type Message = { role: 'staff' | 'assistant'; text: string; action?: PendingAction; alertType?: string; caseId?: string }
type ApiError = Error & { status?: number }
const labelFor = (key: string) => ({ case_id: 'Mã ca', patient_name: 'Bệnh nhân', status: 'Trạng thái', priority: 'Mức ưu tiên', created_at: 'Ngày tạo', appointment_start: 'Bắt đầu', appointment_end: 'Kết thúc', doctor_name: 'Bác sĩ', facility: 'Cơ sở', service: 'Dịch vụ', specialty: 'Chuyên khoa', reason: 'Lý do khám' }[key] || key)

export function StaffAssistantWidget() {
  const dispatch = useDispatch<AppDispatch>()
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [draft, setDraft] = useState('')
  const [conversationId, setConversationId] = useState<string>()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [actionError, setActionError] = useState('')
  const [patientAgreed, setPatientAgreed] = useState(false)
  const input = useRef<HTMLTextAreaElement>(null)
  const launcher = useRef<HTMLButtonElement>(null)
  const wasOpen = useRef(false)
  const focusInputOnOpen = useRef(false)
  const seen = useRef(new Set<string>())
  const lastAlertAt = useRef<string | undefined>(undefined)
  const busyRef = useRef(false)

  useEffect(() => {
    let stopped = false
    let socket: WebSocket | undefined
    let reconnect: ReturnType<typeof setTimeout> | undefined
    let recoveryRetry: ReturnType<typeof setTimeout> | undefined
    let recovering = false
    let attempts = 0
    const addAlert = (alert: StaffAssistantAlert) => {
      if (stopped) return
      if (seen.current.has(alert.event_id)) return
      seen.current.add(alert.event_id)
      if (!lastAlertAt.current || Date.parse(alert.created_at) > Date.parse(lastAlertAt.current)) {
        lastAlertAt.current = alert.created_at
      }
      setOpen(true)
      setMessages((current) => [...current, {
        role: 'assistant',
        text: `${alert.reason} Mã ca: ${alert.case_id.slice(0, 8)}.`,
        alertType: alert.event_type,
        caseId: alert.case_id,
      }])
    }
    const recoverAlerts = async () => {
      if (stopped || recovering) return
      recovering = true
      const since = lastAlertAt.current
        ? new Date(Date.parse(lastAlertAt.current) - 1000).toISOString()
        : undefined
      try {
        const alerts = await fetchStaffAssistantAlerts(since)
        alerts.forEach(addAlert)
        if (!lastAlertAt.current) lastAlertAt.current = new Date().toISOString()
      } catch {
        if (!stopped && !recoveryRetry) {
          recoveryRetry = setTimeout(() => {
            recoveryRetry = undefined
            void recoverAlerts()
          }, 5000)
        }
      } finally {
        recovering = false
      }
    }
    const connect = async () => {
      if (stopped) return
      const ticket = websocketNeedsTicket ? await fetchTakeoverTicket() : null
      if (stopped) return
      try {
        socket = new WebSocket(resolveStaffWorkbenchWebSocketUrl(ticket))
      } catch {
        scheduleReconnect()
        return
      }
      socket.addEventListener('open', () => { attempts = 0; void recoverAlerts() })
      socket.addEventListener('message', (event) => {
        try {
          const payload = JSON.parse(String(event.data)) as {
            type?: string
            alert?: StaffAssistantAlert
            case?: { id?: string; status?: string }
          }
          if (payload.type === 'staff_assistant.alert' && payload.alert) addAlert(payload.alert)
          if (payload.type === 'takeover.case_updated' && payload.case?.id && ['taken_over', 'resolved'].includes(payload.case.status || '')) {
            setMessages((current) => current.filter((message) => message.caseId !== payload.case?.id))
          }
        } catch { /* Ignore unrelated or malformed workbench events. */ }
      })
      socket.addEventListener('close', scheduleReconnect)
      socket.addEventListener('error', () => socket?.close())
    }
    function scheduleReconnect() {
      if (stopped || reconnect) return
      reconnect = setTimeout(() => { reconnect = undefined; attempts += 1; void connect() }, Math.min(1000 * 2 ** attempts, 30000))
    }
    void connect()
    return () => {
      stopped = true
      if (reconnect) clearTimeout(reconnect)
      if (recoveryRetry) clearTimeout(recoveryRetry)
      socket?.close()
    }
  }, [])

  useEffect(() => {
    if (open && focusInputOnOpen.current) {
      input.current?.focus()
      focusInputOnOpen.current = false
    }
    else if (wasOpen.current) launcher.current?.focus()
    wasOpen.current = open
  }, [open])

  const send = async (event?: FormEvent, showMessage = true) => {
    event?.preventDefault()
    const text = draft.trim()
    if (!text || busyRef.current) return
    busyRef.current = true; setBusy(true); setError(''); setActionError(''); setDraft('')
    setMessages((current) => [...current.filter((message) => !message.action), ...(showMessage ? [{ role: 'staff' as const, text }] : [])])
    try {
      setMessages((current) => [...current, { role: 'assistant', text: '' }])
      const reply = await sendStaffMessageStream(
        text,
        conversationId,
        (token) => {
          setMessages((current) => {
            const last = current[current.length - 1]
            if (last && last.role === 'assistant') {
              return [...current.slice(0, -1), { ...last, text: last.text + token }]
            }
            return current
          })
        }
      )
      setConversationId(reply.conversation_id)
      setPatientAgreed(false)
      setMessages((current) => {
        const others = current.slice(0, -1)
        return [...others, { role: 'assistant', text: reply.assistant_text, ...(reply.pending_action ? { action: reply.pending_action } : {}) }]
      })
    } catch (cause) {
      setMessages((current) => {
        const last = current[current.length - 1]
        if (last && last.role === 'assistant' && !last.text) {
          return current.slice(0, -1)
        }
        return current
      })
      const failure = cause as ApiError
      setError(failure.status === 401 ? 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.' : failure.status === 403 ? 'Tài khoản không có quyền dùng trợ lý này.' : failure.message)
      setDraft(text)
    } finally { busyRef.current = false; setBusy(false); input.current?.focus() }
  }

  const act = async (action: PendingAction, confirm: boolean) => {
    if (!conversationId || busyRef.current) return
    busyRef.current = true; setBusy(true); setActionError('')
    try {
      const result = confirm
        ? await confirmStaffAction(conversationId, action.id, patientAgreed)
        : await cancelStaffAction(conversationId, action.id)
      if (confirm && ['booking_review', 'case_booking'].includes(action.kind ?? 'booking_review')) {
        dispatch(clearBookingApprovalPages())
      }
      setMessages((current) => [...current.filter((message) => message.action?.id !== action.id), { role: 'assistant', text: result.assistant_text }])
    } catch (cause) {
      const failure = cause as ApiError
      setActionError(failure.status === 409 || failure.status === 404
        ? 'Đề xuất đã hết hạn hoặc ca/lịch vừa được xử lý. Hãy tra cứu lại trạng thái.'
        : failure.message)
      if (failure.status === 409 || failure.status === 404) {
        setMessages((current) => current.filter((message) => message.action?.id !== action.id))
      }
    } finally { busyRef.current = false; setBusy(false) }
  }

  return <>
    {open && <section aria-label="Trợ lý nhân viên" role="dialog" className="fixed inset-x-3 bottom-20 z-40 flex h-[min(620px,calc(100dvh-7rem))] flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl sm:inset-x-auto sm:right-6 sm:w-[min(420px,calc(100vw-2rem))]">
      <header className="flex items-center justify-between bg-emerald-800 px-4 py-3 text-white"><div className="flex items-center gap-2"><Bot size={20} /><div><h2 className="text-sm font-semibold">Trợ lý nhân viên</h2><p className="text-xs text-emerald-100">Tra cứu thông tin nội bộ</p></div></div><button type="button" aria-label="Đóng trợ lý" onClick={() => setOpen(false)} className="rounded-lg p-2 hover:bg-emerald-700"><X size={18} /></button></header>
      <div aria-live="polite" className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4">
        {messages.length === 0 && <p className="rounded-xl bg-slate-50 p-3 text-sm text-slate-600">Xin chào. Tôi có thể hỗ trợ tra cứu lịch khám, hồ sơ và ca điều phối.</p>}
        {messages.map((message, index) => <article key={`${index}-${message.role}`} role={message.alertType === 'emergency_detected' ? 'alert' : undefined} className={`w-fit min-w-16 max-w-[80%] break-words rounded-xl p-3 text-sm ${message.alertType === 'emergency_detected' ? 'border-2 border-rose-600 bg-rose-50 text-rose-950' : message.role === 'staff' ? 'ml-auto bg-emerald-700 text-white' : 'bg-slate-100 text-slate-800'}`}>
          {message.alertType === 'emergency_detected' && <p className="mb-2 font-bold text-rose-800">🚨 Cấp cứu — cần staff xử lý</p>}
          <p className="whitespace-pre-wrap">{message.text}</p>
          {message.alertType === 'emergency_detected' && message.caseId && <Link to={`/staff/emergency?case=${encodeURIComponent(message.caseId)}`} className="mt-3 inline-flex rounded-lg bg-rose-700 px-3 py-2 font-semibold text-white underline-offset-2 hover:bg-rose-800 focus:outline-none focus:ring-2 focus:ring-rose-500 focus:ring-offset-2">Mở ca cấp cứu</Link>}
          {message.action && <div className="mt-3 rounded-lg border border-amber-300 bg-amber-50 p-3 text-slate-800">
            {(() => {
              const kind = message.action?.kind || 'booking_review'
              const details = kind === 'case_claim' ? message.action?.case_summary : message.action?.booking_summary
              const fields = kind === 'case_claim'
                ? ['case_id', 'patient_name', 'status', 'priority', 'created_at']
                : ['case_id', 'patient_name', 'appointment_start', 'appointment_end', 'doctor_name', 'facility', 'service', 'specialty', 'reason']
              return <>
                <p className="font-semibold">{kind === 'case_claim' ? 'Xác nhận tiếp nhận ca điều phối' : kind === 'case_booking' ? 'Xác nhận tạo booking' : `Xác nhận ${message.action?.decision === 'confirmed' ? 'duyệt lịch' : 'từ chối lịch'}`}</p>
                {fields.map((key) => {
                  const value = details?.[key]
                  return value !== undefined && value !== null && value !== '' ? <p key={key} className="mt-1 text-xs">{labelFor(key)}: {String(value)}</p> : null
                })}
                {kind === 'booking_review' && message.action?.booking_id && <p className="mt-1 text-xs">Mã lịch: {message.action.booking_id}</p>}
                {kind === 'booking_review' && message.action?.reason && <p className="mt-1 text-xs">Lý do: {message.action.reason}</p>}
                {kind === 'case_booking' && <label className="mt-3 flex items-start gap-2 text-xs"><input type="checkbox" checked={patientAgreed} onChange={(event) => setPatientAgreed(event.target.checked)} />Bệnh nhân đã đồng ý thông tin và giờ khám trên booking này.</label>}
                <p className="mt-1 text-xs">Hết hạn: {new Date(message.action!.expires_at).toLocaleString('vi-VN')}</p>
              </>
            })()}
            {actionError && <p role="alert" className="mt-2 text-xs text-rose-700">{actionError}</p>}
            <div className="mt-3 flex gap-2"><button type="button" disabled={busy || (message.action.kind === 'case_booking' && !patientAgreed)} onClick={() => void act(message.action!, true)} className="rounded-lg bg-emerald-700 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">Xác nhận</button><button type="button" disabled={busy} onClick={() => void act(message.action!, false)} className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold disabled:opacity-50">Hủy đề xuất</button></div>
          </div>}
        </article>)}
        {busy && <p role="status" className="text-sm text-slate-500">Đang xử lý…</p>}
        {error && <div role="alert" className="rounded-lg bg-rose-50 p-3 text-sm text-rose-800"><p>{error}</p><button type="button" onClick={() => void send(undefined, false)} disabled={busy} className="mt-2 font-semibold underline">Thử lại</button></div>}
      </div>
      {actionError && !messages.some((message) => message.action) && <p role="alert" className="px-4 text-xs text-rose-700">{actionError}</p>}
      <form onSubmit={(event) => void send(event)} className="flex items-end gap-2 border-t border-slate-200 p-3"><label className="sr-only" htmlFor="staff-assistant-message">Tin nhắn</label><textarea ref={input} id="staff-assistant-message" value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void send() } if (event.key === 'Escape') setOpen(false) }} rows={2} maxLength={4000} placeholder="Nhập câu hỏi…" className="min-h-11 flex-1 resize-none rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100" /><button aria-label="Gửi tin nhắn" type="submit" disabled={busy || !draft.trim()} className="grid h-11 w-11 place-items-center rounded-xl bg-emerald-700 text-white disabled:opacity-50"><Send size={17} /></button></form>
    </section>}
    <button ref={launcher} type="button" aria-label={open ? 'Đóng trợ lý nhân viên' : 'Mở trợ lý nhân viên'} aria-expanded={open} onClick={() => { if (!open) focusInputOnOpen.current = true; setOpen((value) => !value) }} className="fixed bottom-4 right-4 z-40 grid h-14 w-14 place-items-center rounded-full bg-emerald-800 text-white shadow-lg hover:bg-emerald-700 focus:outline-none focus:ring-4 focus:ring-emerald-200 sm:bottom-6 sm:right-6">{open ? <X /> : <MessageSquareText />}</button>
  </>
}
