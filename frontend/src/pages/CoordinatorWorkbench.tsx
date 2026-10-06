import { acceptCaseDetail, canCaseAction } from '../features/coordinator/uiLogic'
import { useOutletContext } from 'react-router-dom'
import type { StaffContext } from '../layouts/StaffLayout'
import { saveAndRefresh } from '../features/coordinator/mutations'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api, canAdminister, dateTime, priorities, statuses, type Case, type CaseDetail, type Catalog, type Dashboard, type Member, type Policy } from '../features/coordinator/api'
import './CoordinatorWorkbench.css'

const sourceNames: Record<string, string> = { chat: 'Hội thoại', consultation: 'Phiếu khám', package: 'Gói khám', booking: 'Lịch chờ duyệt' }
const eventNames: Record<string, string> = { claim: 'Nhận ca', handover: 'Bàn giao', takeover: 'Tiếp quản chat', resume: 'Trả về AI', contact: 'Liên hệ', follow_up: 'Hẹn liên hệ', emergency_detected: 'Phát hiện cảnh báo', emergency_ack: 'Tiếp nhận khẩn', emergency_transfer: 'Bàn giao cấp cứu', complete: 'Hoàn tất', cancel: 'Hủy', plan_updated: 'Đổi phương án khám', deposit_requested: 'Yêu cầu cọc', deposit_verified: 'Xác minh cọc', deposit_expired: 'Hết hạn cọc', booking_confirmed: 'Chốt lịch', refund_request: 'Yêu cầu hoàn cọc', refund_confirm: 'Xác nhận hoàn cọc', intake_submitted: 'Nhận phiếu', human_requested: 'Yêu cầu người hỗ trợ' }
const depositNames: Record<string, string> = { requested: 'Chờ chuyển cọc', verified: 'Đã xác minh', expired: 'Hết hạn', voided: 'Đã thay phương án', refund_pending: 'Chờ hoàn cọc', refunded: 'Đã hoàn cọc' }

interface CarePipelineStep {
  step_number: number;
  anatomical_rank?: number;
  department_name: string;
  target_symptoms?: string[];
  clinical_rationale?: string;
}

function isCarePipelineStep(value: unknown): value is CarePipelineStep {
  if (!value || typeof value !== 'object') return false;
  const step = value as Record<string, unknown>;
  return typeof step.step_number === 'number' &&
    typeof step.department_name === 'string' &&
    (step.anatomical_rank === undefined || typeof step.anatomical_rank === 'number') &&
    (step.target_symptoms === undefined || (Array.isArray(step.target_symptoms) && step.target_symptoms.every((item) => typeof item === 'string'))) &&
    (step.clinical_rationale === undefined || typeof step.clinical_rationale === 'string');
}

function readCarePipelineSteps(value: unknown): CarePipelineStep[] {
  if (!value || typeof value !== 'object') return [];
  const steps = (value as Record<string, unknown>).pipeline_steps;
  return Array.isArray(steps) ? steps.filter(isCarePipelineStep) : [];
}

export default function CoordinatorWorkbench({ mode = 'queue' }: { mode?: 'queue' | 'dashboard' | 'emergency' | 'chat' | 'settings' }) {
  const [params, setParams] = useSearchParams()
  const selectedId = params.get('case')
  const { member: me, updateMember: setMe } = useOutletContext<StaffContext>()
  const [members, setMembers] = useState<Member[]>([])
  const [items, setItems] = useState<Case[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [selected, setSelected] = useState<CaseDetail | null>(null)
  const [catalog, setCatalog] = useState<Catalog | null>(null)
  const [bookingOptions, setBookingOptions] = useState<Catalog | null>(null)
  const [catalogBusy, setCatalogBusy] = useState(false)
  const [dashboard, setDashboard] = useState<Dashboard | null>(null)
  const [policy, setPolicy] = useState<Policy | null>(null)
  const [status, setStatus] = useState('')
  const [search, setSearch] = useState('')
  const [mine, setMine] = useState(false)
  const [error, setError] = useState('')
  const [pollError, setPollError] = useState('')
  const [shiftNote, setShiftNote] = useState('')
  const [shiftHandover, setShiftHandover] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const [note, setNote] = useState('')
  const [handover, setHandover] = useState('')
  const [followUp, setFollowUp] = useState('')
  const [message, setMessage] = useState('')
  const [doctor, setDoctor] = useState('')
  const [specialty, setSpecialty] = useState('')
  const [service, setService] = useState('')
  const [schedule, setSchedule] = useState('')
  const [agreed, setAgreed] = useState(false)
  const [amount, setAmount] = useState('')
  const [reference, setReference] = useState('')
  const [evidence, setEvidence] = useState('')
  const [policyForm, setPolicyForm] = useState({ hold_minutes: '', response_minutes: '', emergency_response_minutes: '', payment_instructions: '', refund_policy: '' })
  const [account, setAccount] = useState({ user_id: '', clinical_qualification: '', facility_ids: '', is_admin: false, enabled: true })
  const busyRef = useRef(false)
  const selectedRef = useRef(selectedId); selectedRef.current = selectedId
  const requestGeneration = useRef(0)
  const statsAt = useRef(0)
  const detailGeneration = useRef(0)
  const resourcesReady = useRef(false)
  const admin = canAdminister(me)
  const canReceive = (member: Member) => member.user_id !== me?.user_id && member.on_duty && (!member.facility_ids.length || !selected?.facility_id || member.facility_ids.includes(selected.facility_id))
  const carePipelineSteps = readCarePipelineSteps(selected?.ai_snapshot.care_pipeline)

  const load = useCallback(async () => {
    const query = new URLSearchParams({ offset: String(offset), limit: '30' })
    if (status) query.set('status', status)
    if (search.trim()) query.set('q', search.trim())
    if (mine) query.set('mine', 'true')
    if (mode === 'emergency') query.set('priority', '0')
    if (mode === 'chat') query.set('conversations', 'true')
    const generation = ++requestGeneration.current
    const refreshStats = Date.now() - statsAt.current >= 30000
    const list = await api<{ items: Case[]; total: number }>('/cases?' + query)
    if (generation !== requestGeneration.current) return
    setItems(list.items); setTotal(list.total)
    if (refreshStats) {
      const [stats, people, identity] = await Promise.all([api<Dashboard>('/dashboard'), api<Member[]>('/members'), api<Member>('/me')])
      if (generation !== requestGeneration.current) return
      setDashboard(stats); setMembers(people); setMe(identity); statsAt.current = Date.now()
    }
    if (!resourcesReady.current && mode !== 'chat') {
      const [options, p] = await Promise.all([api<Catalog>('/catalog'), api<Policy | null>('/policy')])
      if (generation !== requestGeneration.current) return
      setCatalog(options); setPolicy(p)
      if (p) setPolicyForm({ hold_minutes: String(p.hold_minutes), response_minutes: String(p.response_minutes), emergency_response_minutes: String(p.emergency_response_minutes), payment_instructions: p.payment_instructions, refund_policy: p.refund_policy })
      resourcesReady.current = true
    }
    const id = selectedRef.current
    if (id) {
      const detailRequest = ++detailGeneration.current
      const value = await api<CaseDetail>('/cases/' + id)
      if (generation === requestGeneration.current && detailRequest === detailGeneration.current) setSelected(current => acceptCaseDetail(current, value, selectedRef.current))
    }
    setLoading(false)
  }, [offset, status, search, mine, mode, setMe])
  useEffect(() => {
    let stopped = false
    let timer: ReturnType<typeof setTimeout>
    const poll = async () => {
      if (!busyRef.current) try { await load(); if (!stopped) setPollError('') } catch (e) { if (!stopped) { setPollError(e instanceof Error ? e.message : 'Không thể tải dữ liệu.'); setLoading(false) } }
      if (!stopped) timer = setTimeout(poll, 5000)
    }
    void poll()
    return () => { stopped = true; clearTimeout(timer); requestGeneration.current += 1 }
  }, [load])
  useEffect(() => {
    let active = true
    const detailRequest = ++detailGeneration.current
    setSelected(null); setNote(''); setMessage(''); setReference(''); setEvidence(''); setAgreed(false); setDoctor(''); setSpecialty(''); setService(''); setSchedule(''); setAmount(''); setHandover(''); setFollowUp(''); setError(''); setNotice('')
    if (selectedId) void api<CaseDetail>('/cases/' + selectedId).then(value => {
      if (active && detailRequest === detailGeneration.current) setSelected(current => acceptCaseDetail(current, value, selectedRef.current))
    }).catch(e => { if (active && detailRequest === detailGeneration.current) setError(e.message) })
    return () => { active = false; detailGeneration.current += 1 }
  }, [selectedId])
  useEffect(() => {
    let stopped = false
    setBookingOptions(null)
    setCatalogBusy(Boolean(doctor))
    if (doctor) void api<Catalog>('/catalog?doctor_id=' + doctor).then(value => {
      if (stopped) return
      setBookingOptions(value)
      setSpecialty(current => value.specialties.some(x => x.id === current) ? current : '')
      setService(current => value.services.some(x => x.id === current) ? current : '')
      setSchedule(current => value.schedules.some(x => x.id === current) ? current : '')
    }).catch(e => { if (!stopped) setError(e.message) }).finally(() => { if (!stopped) setCatalogBusy(false) })
    return () => { stopped = true }
  }, [doctor])
  const run = async (task: () => Promise<unknown>, success: string) => {
    if (busyRef.current) return
    detailGeneration.current += 1
    busyRef.current = true; setBusy(true); setError(''); setNotice('')
    requestGeneration.current += 1
    try {
      const outcome = await saveAndRefresh(task, result => {
        if (result && typeof result === 'object') {
          if ('id' in result && 'version' in result) {
            const detail = result as CaseDetail
            setSelected(current => acceptCaseDetail(current, detail, selectedRef.current))
          }
          if ('on_duty' in result && typeof result.on_duty === 'boolean') {
            const onDuty = result.on_duty
            setMe(current => current ? { ...current, on_duty: onDuty } : current)
          }
        }
        setNotice(success); statsAt.current = 0
      }, load)
      if (!outcome.refreshed) setError('Thao tác đã lưu thành công, nhưng chưa tải lại được dữ liệu. Hãy làm mới để xem trạng thái mới nhất.')
    } catch (e) { setError(e instanceof Error ? e.message : 'Thao tác thất bại.') }
    finally { busyRef.current = false; setBusy(false) }
  }
  const act = (action: string) => selected && run(() => api<CaseDetail>('/cases/' + selected.id + '/actions', 'POST', { version: selected.version, action, note, assigned_to: handover || null, follow_up_at: followUp ? new Date(followUp).toISOString() : null, reference: reference || null }), 'Đã lưu thao tác.')
  const owned = Boolean(selected && me && selected.assigned_to === me.user_id)
  const allowed = (action: string) => canCaseAction(selected, me, action)
  const choose = (id: string) => setParams({ case: id })
  const person = (id: string | null) => members.find(x => x.user_id === id)?.name || (id ? 'Nhân viên đã ngừng hoạt động' : 'Chưa nhận')
  if (mode === 'chat') return <div className="coordinator-workbench cw-chat-workspace">
    <header className="cw-heading"><div><h1>Hội thoại bệnh nhân</h1><p>Theo dõi hội thoại với AI, tiếp quản và trả lời trực tiếp cho bệnh nhân.</p></div><button disabled={busy} onClick={() => void load().catch(e => setPollError(e.message))}>Làm mới</button></header>
    {pollError && <p className="cw-error" role="alert">{pollError}</p>}{error && <p className="cw-error" role="alert">{error}</p>}{notice && <p className="cw-notice" role="status">{notice}</p>}
    {me && <div className="cw-actions"><strong>{me.name} · {me.on_duty ? 'Đang trực' : 'Chưa bắt đầu ca trực'}</strong><button disabled={busy || me.on_duty} onClick={() => void run(() => api('/duty/start', 'POST'), 'Đã bắt đầu ca trực.')}>Bắt đầu ca trực</button><button disabled={busy || !me.on_duty} onClick={() => void run(() => api('/duty/end', 'POST'), 'Đã kết thúc ca trực.')}>Kết thúc ca trực</button></div>}
    <div className="cw-chat-layout">
      <section className="cw-panel cw-conversation-list" aria-label="Danh sách hội thoại">
        <h2>Danh sách hội thoại</h2>
        <label>Tìm bệnh nhân<input placeholder="Tên, điện thoại hoặc mã ca" value={search} onChange={e => { setSearch(e.target.value); setOffset(0) }} /></label>
        <label>Trạng thái<select value={status} onChange={e => { setStatus(e.target.value); setOffset(0) }}><option value="">Tất cả hội thoại</option>{Object.entries(statuses).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
        <label className="cw-check"><input type="checkbox" checked={mine} onChange={e => { setMine(e.target.checked); setOffset(0) }} />Hội thoại của tôi</label>
        {loading && <p role="status">Đang tải hội thoại…</p>}
        {items.map(item => <button key={item.id} className={'cw-conversation-card' + (item.id === selectedId ? ' cw-conversation-active' : '')} onClick={() => choose(item.id)}>
          <strong>{item.patient.name || 'Bệnh nhân chưa cung cấp tên'}</strong><small>{item.patient.phone || 'Chưa có điện thoại'} · {item.id.slice(0, 8).toUpperCase()}</small>
          <span className={item.priority === 0 ? 'cw-critical' : ''}>{item.priority === 0 ? 'Cảnh báo cấp cứu · ' : ''}{item.control === 'human' ? 'Điều phối viên đang trả lời' : 'AI đang hỗ trợ'}</span>
          <small>{statuses[item.status] || item.status} · {person(item.assigned_to)}</small><small>{dateTime(item.created_at)}</small>
        </button>)}
        {!loading && !items.length && <p className="cw-empty">Không có hội thoại phù hợp.</p>}
        <footer className="cw-pagination"><span>{total} hội thoại</span><button disabled={!offset} onClick={() => setOffset(Math.max(0, offset - 30))}>Trước</button><button disabled={offset + 30 >= total} onClick={() => setOffset(offset + 30)}>Sau</button></footer>
      </section>
      <section className="cw-panel cw-conversation-thread" aria-label="Nội dung hội thoại">
        {!selectedId ? <div className="cw-chat-placeholder"><h2>Chọn một hội thoại để xem tin nhắn</h2><p>Bạn có thể theo dõi AI hoặc nhận ca và tiếp quản để trả lời trực tiếp.</p></div> : !selected ? <p role="status">Đang tải hội thoại…</p> : <>
          <header className="cw-heading"><div><h2>{selected.patient.name || 'Hội thoại bệnh nhân'}</h2><small>{selected.patient.phone || 'Chưa có điện thoại'} · {person(selected.assigned_to)}</small><p>{selected.control === 'human' ? 'Điều phối viên đang trả lời; AI tạm dừng.' : 'AI đang hỗ trợ bệnh nhân.'}</p></div><button onClick={() => setParams({})}>Đóng hội thoại</button></header>
          {selected.priority === 0 && <div className="cw-emergency"><strong>Hội thoại có cảnh báo cấp cứu</strong><p>Tiếp nhận và ghi diễn biến trong trang xử lý cấp cứu.</p><Link to={'/staff/emergency?case=' + encodeURIComponent(selected.id)}>Mở ca cấp cứu</Link></div>}
          <div className="cw-actions"><button disabled={busy || !me?.on_duty || ['completed', 'cancelled'].includes(selected.status) || Boolean(selected.assigned_to && !owned)} onClick={() => void act('claim')}>Nhận ca</button><button disabled={busy || !allowed('takeover')} onClick={() => void act('takeover')}>Tiếp quản từ AI</button>{selected.status !== 'observing' && <Link to={'/staff/queue?case=' + encodeURIComponent(selected.id)}>Mở phiếu điều phối và xếp lịch</Link>}</div>
          <div className="cw-messages cw-chat-messages" role="log" aria-label="Tin nhắn bệnh nhân và nhân viên">
            {selected.messages.length ? selected.messages.map(m => <article key={m.id} className={'cw-message-' + m.sender}><strong>{m.sender === 'patient' ? 'Bệnh nhân' : m.sender === 'coordinator' ? person(m.actor_id) : m.sender === 'ai' ? 'AI' : 'Thông báo'}</strong><time>{dateTime(m.created_at)}</time><p>{m.body}</p></article>) : <p>Chưa có tin nhắn được lưu.</p>}
          </div>
          <form onSubmit={e => { e.preventDefault(); if (!allowed('message') || !message.trim()) return; const body = message.trim(); const caseId = selected.id; void run(async () => { await api('/cases/' + caseId + '/messages', 'POST', { client_id: crypto.randomUUID(), body }); if (selectedRef.current === caseId) setMessage('') }, 'Đã gửi tin nhắn.') }}>
            <label>Trả lời bệnh nhân<textarea maxLength={5000} disabled={busy || !allowed('message')} required value={message} onChange={e => setMessage(e.target.value)} placeholder="Nhận ca và tiếp quản từ AI để trả lời bệnh nhân." /></label><button className="cw-primary" disabled={busy || !allowed('message') || !message.trim()}>Gửi tin nhắn</button>
          </form>
          {selected.control === 'human' && <details className="cw-chat-resume"><summary>Trả hội thoại về AI</summary><label>Tóm tắt nội dung đã hỗ trợ<textarea value={note} onChange={e => setNote(e.target.value)} placeholder="Ghi thông tin AI cần biết để tiếp tục hỗ trợ." /></label><button disabled={busy || !allowed('resume') || !note.trim()} onClick={() => void act('resume')}>Trả về AI kèm tóm tắt</button></details>}
        </>}
      </section>
    </div>
  </div>
  const title = mode === 'dashboard' ? 'Tổng quan điều phối' : mode === 'emergency' ? 'Ưu tiên cấp cứu' : mode === 'settings' ? 'Tài khoản và chính sách' : 'Hàng đợi điều phối'
  return <div className="coordinator-workbench">
    <header className="cw-heading"><div><h1>{title}</h1><p>Điều hướng khám và hỗ trợ bệnh nhân. Không chẩn đoán xác định hoặc kê đơn.</p></div><button disabled={busy} onClick={() => { statsAt.current = 0; void load().then(() => { setPollError(''); setNotice('Đã cập nhật dữ liệu.') }).catch(e => setPollError(e.message)) }}>Làm mới</button></header>
    {pollError && <p className="cw-error" role="alert">Tải dữ liệu: {pollError}</p>}{error && <p className="cw-error" role="alert">{error}</p>}{notice && <p className="cw-notice" role="status">{notice}</p>}
    {loading && <p role="status">Đang tải dữ liệu…</p>}
    {me && <section className="cw-panel"><div className="cw-actions"><strong>{me.name} · {me.on_duty ? 'Đang trực' : 'Chưa bắt đầu ca trực'}</strong><button disabled={busy || me.on_duty} onClick={() => void run(() => api('/duty/start', 'POST'), 'Đã bắt đầu ca trực.')}>Bắt đầu ca trực</button><button disabled={busy || !me.on_duty} onClick={() => void run(() => api('/duty/end', 'POST'), 'Đã kết thúc ca trực.')}>Kết thúc ca trực</button></div><details><summary>Bàn giao toàn bộ ca đang xử lý và kết thúc ca trực</summary><label>Điều phối viên nhận ca<select value={shiftHandover} onChange={e => setShiftHandover(e.target.value)}><option value="">Chọn người đang trực</option>{members.filter(m => m.user_id !== me.user_id && m.on_duty).map(m => <option key={m.user_id} value={m.user_id}>{m.name}</option>)}</select></label><label>Tóm tắt bàn giao<textarea value={shiftNote} onChange={e => setShiftNote(e.target.value)} /></label><button disabled={busy || !me.on_duty || !shiftHandover || !shiftNote.trim()} onClick={() => void run(() => api('/duty/handover', 'POST', { assigned_to: shiftHandover, note: shiftNote }), 'Đã bàn giao ca trực.')}>Bàn giao và kết thúc ca trực</button></details></section>}
    {mode === 'settings' ? <div className="cw-columns"><section className="cw-panel"><h2>Chính sách vận hành</h2><p>Nhập điều khoản áp dụng thực tế. Chưa cấu hình sẽ không thể yêu cầu cọc.</p><form onSubmit={e => { e.preventDefault(); void run(async () => { const p = await api<Policy>('/policy', 'PUT', { ...policyForm, hold_minutes: Number(policyForm.hold_minutes), response_minutes: Number(policyForm.response_minutes), emergency_response_minutes: Number(policyForm.emergency_response_minutes) }); setPolicy(p) }, 'Đã lưu chính sách.') }}>
      <label>Thời hạn giữ chỗ (phút)<input type="number" min="5" max="1440" required value={policyForm.hold_minutes} onChange={e => setPolicyForm({ ...policyForm, hold_minutes: e.target.value })} /></label>
      <label>Hạn tiếp nhận thông thường (phút)<input type="number" min="1" required value={policyForm.response_minutes} onChange={e => setPolicyForm({ ...policyForm, response_minutes: e.target.value })} /></label>
      <label>Hạn tiếp nhận cấp cứu (phút)<input type="number" min="1" max="60" required value={policyForm.emergency_response_minutes} onChange={e => setPolicyForm({ ...policyForm, emergency_response_minutes: e.target.value })} /></label>
      <label>Hướng dẫn chuyển cọc<textarea required minLength={10} value={policyForm.payment_instructions} onChange={e => setPolicyForm({ ...policyForm, payment_instructions: e.target.value })} /></label><label>Điều kiện đổi/hủy/hoàn cọc<textarea required minLength={10} value={policyForm.refund_policy} onChange={e => setPolicyForm({ ...policyForm, refund_policy: e.target.value })} /></label><button className="cw-primary" disabled={busy || !admin}>Lưu chính sách</button>
    </form></section><section className="cw-panel"><h2>Điều phối viên</h2><ul>{members.map(m => <li key={m.user_id}>{m.name} · {m.clinical_qualification}{m.is_admin ? ' · Quản trị' : ''}<small>{m.user_id}</small></li>)}</ul><form onSubmit={e => { e.preventDefault(); void run(() => api('/members', 'PUT', { ...account, facility_ids: account.facility_ids.split(',').map(x => x.trim()).filter(Boolean) }), 'Đã lưu quyền tài khoản.') }}><label>ID tài khoản đã xác thực<input required value={account.user_id} onChange={e => setAccount({ ...account, user_id: e.target.value })} /></label><label>Thông tin chuyên môn<input required value={account.clinical_qualification} onChange={e => setAccount({ ...account, clinical_qualification: e.target.value })} /></label><label>ID cơ sở được phép (phân cách dấu phẩy; để trống nếu toàn hệ thống)<input value={account.facility_ids} onChange={e => setAccount({ ...account, facility_ids: e.target.value })} /></label><label className="cw-check"><input type="checkbox" checked={account.is_admin} onChange={e => setAccount({ ...account, is_admin: e.target.checked })} />Quản trị điều phối</label><label className="cw-check"><input type="checkbox" checked={account.enabled} onChange={e => setAccount({ ...account, enabled: e.target.checked })} />Cho phép hoạt động</label><button disabled={busy || !admin}>Lưu quyền</button></form></section></div> : <>
      {dashboard && <section className="cw-stats"><div><span>Chưa nhận</span><strong>{dashboard.counts.new || 0}</strong></div><div><span>Cấp cứu đang mở</span><strong>{dashboard.emergency}</strong></div><div><span>Quá hạn xử lý</span><strong>{dashboard.overdue}</strong></div><div><span>Chờ cọc</span><strong>{dashboard.counts.waiting_deposit || 0}</strong></div></section>}
      {mode === 'dashboard' && dashboard && <section className="cw-panel"><h2>Nhắc việc đến hạn</h2>{dashboard.followups.length ? dashboard.followups.map(c => <button key={c.id} onClick={() => choose(c.id)}>{c.patient.name || 'Chưa có tên'} · {dateTime(c.follow_up_at)} · {person(c.assigned_to)}</button>) : <p>Không có nhắc việc đến hạn.</p>}</section>}
      <section className="cw-toolbar"><label>Tìm ca<input placeholder="Tên, điện thoại hoặc mã ca" value={search} onChange={e => { setSearch(e.target.value); setOffset(0) }} /></label><label>Trạng thái<select value={status} onChange={e => { setStatus(e.target.value); setOffset(0) }}><option value="">Tất cả</option>{Object.entries(statuses).filter(([k]) => k !== 'observing').map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label><label className="cw-check"><input type="checkbox" checked={mine} onChange={e => { setMine(e.target.checked); setOffset(0) }} />Ca của tôi</label></section>
      <div className={'cw-grid' + (selectedId ? ' cw-with-detail' : '')}><section className="cw-panel cw-queue"><div className="cw-table-wrap"><table><thead><tr><th>Bệnh nhân / mã</th><th>Ưu tiên</th><th>Trạng thái</th><th>Phụ trách</th><th>Tạo lúc</th></tr></thead><tbody>{items.map(c => <tr key={c.id} className={c.id === selectedId ? 'cw-selected' : ''}><td><button onClick={() => choose(c.id)} className="cw-link">{c.patient.name || 'Chưa có tên'}</button><small>{c.patient.phone || 'Chưa có điện thoại'} · {sourceNames[c.source] || c.source}</small><small>{c.id.slice(0, 8).toUpperCase()}</small></td><td className={c.priority === 0 ? 'cw-critical' : ''}>{priorities[c.priority]}</td><td>{statuses[c.status] || c.status}</td><td>{person(c.assigned_to)}</td><td>{dateTime(c.created_at)}</td></tr>)}</tbody></table></div>{!loading && !items.length && <p className="cw-empty">Không có ca phù hợp.</p>}<footer className="cw-pagination"><span>{total} ca</span><button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 30))}>Trước</button><button disabled={offset + 30 >= total} onClick={() => setOffset(offset + 30)}>Sau</button></footer></section>
      {selectedId && <aside className="cw-detail"><button onClick={() => setParams({})}>Đóng hồ sơ</button>{!selected ? <p>Đang tải hồ sơ…</p> : <>
        <section className="cw-panel"><h2>{selected.patient.name || 'Hồ sơ ca'}</h2><small>Mã {selected.id} · phiên bản {selected.version}</small><p>{statuses[selected.status]} · {priorities[selected.priority]} · {person(selected.assigned_to)}</p><dl>{Object.entries(selected.patient).filter(([, v]) => v).map(([k, v]) => <div key={k}><dt>{{ name: 'Họ tên', phone: 'Điện thoại', email: 'Email', date_of_birth: 'Ngày sinh', gender: 'Giới tính', guardian_name: 'Người giám hộ', guardian_phone: 'Liên hệ giám hộ', preferred_date: 'Ngày mong muốn', preferred_period: 'Buổi mong muốn', facility_preference: 'Cơ sở mong muốn', contact_time_preference: 'Thời gian liên hệ', notes: 'Nội dung yêu cầu', consent_to_contact: 'Đồng ý liên hệ' }[k] || k}</dt><dd>{String(v)}</dd></div>)}</dl><p>Hạn xử lý: {dateTime(selected.due_at)}. Nhắc việc: {dateTime(selected.follow_up_at)}</p><button disabled={busy || !me?.on_duty || ['completed', 'cancelled'].includes(selected.status) || Boolean(selected.assigned_to && !owned)} onClick={() => void act('claim')}>Nhận ca</button></section>
        <section className="cw-panel cw-ai-panel">
          <h2>Kết quả Định hướng Lâm sàng (AI Triage & Care Pipeline)</h2>
          {Object.keys(selected.ai_snapshot).length ? (
            <>
              <div className="cw-ai-badges">
                {selected.ai_snapshot.ats_level ? (
                  <span className={`cw-ats-badge cw-ats-${selected.ai_snapshot.ats_level}`}>
                    ATS Cấp {String(selected.ai_snapshot.ats_level)}: {
                      selected.ai_snapshot.ats_level === 1 ? 'CẤP CỨU KHẨN CẤP' :
                      selected.ai_snapshot.ats_level === 2 ? 'NGUY CƠ CAO (≤ 24h)' :
                      selected.ai_snapshot.ats_level === 3 ? 'BÁN KHẨN (≤ 3 ngày)' : 'TIÊU CHUẨN (≤ 7 ngày)'
                    }
                  </span>
                ) : null}
                {selected.ai_snapshot.max_booking_days !== undefined && (
                  <span className="cw-window-badge">
                    Cửa sổ khám: <strong>{String(selected.ai_snapshot.max_booking_days)} ngày</strong>
                  </span>
                )}
              </div>

              {selected.ai_snapshot.emergency_warning && (
                <div className="cw-emergency-banner" role="alert">
                  <strong>🚨 CẢNH BÁO LÂM SÀNG CẤP CỨU:</strong>
                  <p>{String(selected.ai_snapshot.emergency_warning)}</p>
                </div>
              )}

              {/* LỘ TRÌNH KHÁM PHÂN TẦNG ĐA KHOA (STAGED CARE NAVIGATION PIPELINE) */}
              {carePipelineSteps.length ? (
                <div className="cw-pipeline-container">
                  <div className="cw-pipeline-header">
                    <strong>🏥 Lộ trình Khám Ưu tiên Phân tầng (Staged Care Navigation):</strong>
                    <small>Nguyên tắc y khoa: Cơ quan sinh tồn luôn được ưu tiên khám trước mức độ đau đơn thuần.</small>
                  </div>
                  <div className="cw-pipeline-steps">
                    {carePipelineSteps.map((step) => (
                      <div key={step.step_number} className={`cw-step-card ${step.step_number === 1 ? 'cw-step-primary' : 'cw-step-secondary'}`}>
                        <div className="cw-step-badge">
                          Bước {step.step_number} {step.anatomical_rank === 1 ? '· Sinh tồn' : step.anatomical_rank === 2 ? '· Nội tạng chính' : '· Ngoại vi'}
                        </div>
                        <div className="cw-step-content">
                          <h4 className="cw-step-title">{step.department_name}</h4>
                          {step.target_symptoms?.length ? (
                            <p className="cw-step-symptoms">
                              <strong>Triệu chứng:</strong> {step.target_symptoms.join(', ')}
                            </p>
                          ) : null}
                          {step.clinical_rationale && (
                            <p className="cw-step-rationale">{step.clinical_rationale}</p>
                          )}
                          <button
                            type="button"
                            className="cw-apply-btn"
                            disabled={busy || !owned}
                            onClick={() => {
                              const matched = catalog?.specialties.find(
                                s => s.name.toLowerCase().includes(step.department_name.toLowerCase()) ||
                                     step.department_name.toLowerCase().includes(s.name.toLowerCase())
                              );
                              if (matched) {
                                setSpecialty(matched.id);
                                setNote(`Định hướng theo Lộ trình Khám phân tầng AI: Bước ${step.step_number} (${step.department_name})`);
                                setNotice(`Đã nạp "${matched.name}" vào Phương án khám bên dưới.`);
                              } else {
                                setNote(`Định hướng theo Lộ trình Khám phân tầng AI: Bước ${step.step_number} (${step.department_name})`);
                                setNotice(`Đã ghi nhận Bước ${step.step_number} (${step.department_name}). Vui lòng chọn chuyên khoa phù hợp.`);
                              }
                            }}
                          >
                            Áp dụng Bước {step.step_number} vào phương án
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : selected.ai_snapshot.suggested_department_name ? (
                <div className="cw-single-specialty-card">
                  <div>
                    <strong>Chuyên khoa khuyến nghị:</strong>
                    <h3>{String(selected.ai_snapshot.suggested_department_name)}</h3>
                  </div>
                  <button
                    type="button"
                    className="cw-apply-btn"
                    disabled={busy || !owned}
                    onClick={() => {
                      const deptName = String(selected.ai_snapshot.suggested_department_name);
                      const matched = catalog?.specialties.find(
                        s => s.name.toLowerCase().includes(deptName.toLowerCase()) ||
                             deptName.toLowerCase().includes(s.name.toLowerCase())
                      );
                      if (matched) {
                        setSpecialty(matched.id);
                        setNote(`Khám theo khuyến nghị AI: ${deptName}`);
                        setNotice(`Đã nạp "${matched.name}" vào Phương án khám.`);
                      }
                    }}
                  >
                    Áp dụng vào phương án
                  </button>
                </div>
              ) : null}

              <details className="cw-details-raw">
                <summary>Dữ kiện lâm sàng & Phân tích chi tiết</summary>
                <pre>{JSON.stringify(selected.ai_snapshot, null, 2)}</pre>
              </details>
            </>
          ) : (
            <p>Phiếu này chưa có kết quả AI được lưu.</p>
          )}
        </section>
        <section className="cw-panel"><h2>Liên hệ và bàn giao</h2><label>Kết quả liên hệ / lý do thao tác<textarea value={note} onChange={e => setNote(e.target.value)} /></label><div className="cw-actions"><button disabled={busy || !owned || !note.trim() || !allowed('contact')} onClick={() => void act('contact')}>Lưu kết quả liên hệ</button><button disabled={busy || !owned || !note.trim() || !allowed('complete')} onClick={() => void act('complete')}>Hoàn tất ca</button><button disabled={busy || !owned || !note.trim() || !allowed('cancel')} onClick={() => void act('cancel')}>Hủy ca</button></div><label>Nhắc liên hệ lúc<input type="datetime-local" value={followUp} onChange={e => setFollowUp(e.target.value)} /></label><button disabled={busy || !allowed('follow_up') || !followUp || new Date(followUp).getTime() <= Date.now() || !Number.isFinite(new Date(followUp).getTime())} onClick={() => void act('follow_up')}>Đặt nhắc việc</button><label>Người nhận bàn giao<select value={handover} onChange={e => setHandover(e.target.value)}><option value="">Chọn điều phối viên</option>{members.filter(canReceive).map(m => <option key={m.user_id} value={m.user_id}>{m.name}</option>)}</select></label><button disabled={busy || !owned || !handover || !note.trim() || !allowed('handover')} onClick={() => void act('handover')}>Bàn giao ca</button>{selected.priority === 0 && <div className="cw-emergency"><h3>Xử lý cấp cứu</h3><p>Ghi diễn biến và đơn vị tiếp nhận thực tế trong phần ghi chú.</p><button disabled={busy || !owned || !note.trim() || !allowed('emergency_ack')} onClick={() => void act('emergency_ack')}>Ghi nhận tiếp nhận khẩn</button><button disabled={busy || !owned || !note.trim() || !allowed('emergency_transfer')} onClick={() => void act('emergency_transfer')}>Ghi nhận bàn giao cấp cứu</button></div>}</section>
        {selected.session_id && <section className="cw-panel"><h2>Hội thoại</h2><p>{selected.control === 'human' ? 'Bác sĩ điều phối đang trả lời; AI tạm dừng.' : 'AI đang trả lời.'}</p><div className="cw-actions"><button disabled={busy || !allowed('takeover')} onClick={() => void act('takeover')}>Tiếp quản</button><button disabled={busy || !allowed('resume') || !note.trim()} onClick={() => void act('resume')}>Trả về AI kèm tóm tắt</button></div><div className="cw-messages">{selected.messages.map(m => <article key={m.id}><strong>{m.sender === 'patient' ? 'Bệnh nhân' : m.sender === 'coordinator' ? person(m.actor_id) : m.sender === 'ai' ? 'AI' : 'Thông báo'}</strong><time>{dateTime(m.created_at)}</time><p>{m.body}</p></article>)}</div><form onSubmit={e => { e.preventDefault(); const body = message; const caseId = selected.id; void run(async () => { await api('/cases/' + caseId + '/messages', 'POST', { client_id: crypto.randomUUID(), body }); if (selectedRef.current === caseId) setMessage('') }, 'Đã gửi tin nhắn.') }}><label>Tư vấn điều hướng<textarea required value={message} onChange={e => setMessage(e.target.value)} placeholder="Hỏi rõ triệu chứng, giải thích chuyên khoa hoặc hướng dẫn bước tiếp theo." /></label><button className="cw-primary" disabled={busy || !allowed('message') || !message.trim()}>Gửi tới bệnh nhân</button></form></section>}
        {selected.priority !== 0 && <section className="cw-panel"><h2>Phương án khám</h2>{selected.plan.starts_at && <p>Phương án hiện tại: {dateTime(String(selected.plan.starts_at))} · {catalog?.doctors.find(d => d.id === selected.plan.doctor_id)?.name || 'Bác sĩ đã chọn'}</p>}<form onSubmit={e => { e.preventDefault(); void run(() => api('/cases/' + selected.id + '/plan', 'PUT', { version: selected.version, specialty_id: specialty, service_id: service, schedule_id: schedule, reason: note, patient_agreed: agreed }), 'Đã lưu phương án khám.') }}><label>Bác sĩ<select required value={doctor} onChange={e => { setDoctor(e.target.value); setSchedule('') }}><option value="">Chọn bác sĩ</option>{catalog?.doctors.map(x => <option key={x.id} value={x.id}>{x.name}</option>)}</select></label><label>Chuyên khoa<select required value={specialty} onChange={e => setSpecialty(e.target.value)}><option value="">Chọn chuyên khoa</option>{bookingOptions?.specialties.map(x => <option key={x.id} value={x.id}>{x.name}</option>)}</select></label><label>Dịch vụ<select required value={service} onChange={e => setService(e.target.value)}><option value="">Chọn dịch vụ</option>{bookingOptions?.services.map(x => <option key={x.id} value={x.id}>{x.name}</option>)}</select></label><label>Giờ và cơ sở<select required value={schedule} onChange={e => setSchedule(e.target.value)}><option value="">Chọn lịch đã công bố</option>{bookingOptions?.schedules.map(x => <option key={x.id} value={x.id}>{dateTime(x.starts_at)} · {bookingOptions.facilities.find(f => f.id === x.facility_id)?.name || 'Cơ sở'}</option>)}</select></label><label className="cw-check"><input type="checkbox" checked={agreed} onChange={e => setAgreed(e.target.checked)} />Bệnh nhân đã đồng ý phương án và điều khoản áp dụng</label><p>Lý do điều chỉnh lấy từ phần ghi chú xử lý ở trên. Lưu phương án chưa giữ chỗ.</p><button disabled={busy || catalogBusy || !bookingOptions || !owned || !agreed || !note.trim() || ['cancelled', 'completed'].includes(selected.status)}>Lưu phương án / đổi lịch</button></form></section>}
        {selected.priority !== 0 && <section className="cw-panel"><h2>Cọc và xác nhận lịch</h2><p>Xác minh thủ công trên giao dịch thực tế. Không tự động thu hoặc hoàn tiền.</p>{!policy && <p>Chưa cấu hình điều khoản cọc.</p>}{selected.deposits.map(d => <article className="cw-deposit" key={d.id}><strong>{d.amount.toLocaleString('vi-VN')} {d.currency} · {depositNames[d.status] || d.status}</strong><p>Hạn: {dateTime(d.expires_at)}</p><p>{d.instructions}</p><p>Hoàn cọc: {d.refund_policy}</p>{d.transaction_reference && <p>Mã giao dịch: {d.transaction_reference}</p>}</article>)}<form onSubmit={e => { e.preventDefault(); void run(() => api('/cases/' + selected.id + '/deposits', 'POST', { version: selected.version, amount: Number(amount) }), 'Đã giữ chỗ và gửi yêu cầu cọc.') }}><label>Số tiền cọc (VND)<input type="number" required min="1" value={amount} onChange={e => setAmount(e.target.value)} /></label><button disabled={busy || !owned || !policy || selected.status !== 'planned'}>Giữ chỗ và yêu cầu cọc</button></form><label>Mã giao dịch chuyển/hoàn cọc<input value={reference} onChange={e => setReference(e.target.value)} /></label><label>Bằng chứng đã đối soát<textarea value={evidence} onChange={e => setEvidence(e.target.value)} placeholder="Thông tin giao dịch từ nguồn thanh toán đã kiểm tra." /></label><div className="cw-actions"><button disabled={busy || !owned || !['waiting_deposit', 'deposit_expired'].includes(selected.status) || !reference.trim() || !evidence.trim()} onClick={() => void run(() => api('/cases/' + selected.id + '/verify-deposit', 'POST', { version: selected.version, reference, evidence }), 'Đã xác minh khoản cọc.')}>Xác minh cọc</button><button className="cw-primary" disabled={busy || !owned || selected.status !== 'deposit_verified'} onClick={() => void run(() => api('/cases/' + selected.id + '/confirm', 'POST', { version: selected.version }), 'Đã chốt lịch và lưu thông báo.')}>Chốt lịch</button><button disabled={busy || !owned || !note.trim() || !allowed('refund_request')} onClick={() => void act('refund_request')}>Yêu cầu hoàn cọc</button><button disabled={busy || !owned || !note.trim() || !reference.trim() || !allowed('refund_confirm')} onClick={() => void act('refund_confirm')}>Xác nhận đã hoàn cọc</button></div></section>}
        <section className="cw-panel"><h2>Lịch sử thao tác</h2>{selected.events.length ? selected.events.map(e => <article key={e.id} className="cw-event"><strong>{eventNames[e.action] || e.action}</strong><small>{dateTime(e.created_at)} · {person(e.actor_id)}</small>{e.note && <p>{e.note}</p>}</article>) : <p>Chưa có thao tác.</p>}</section>
      </>}</aside>}
      </div>
    </>}
  </div>
}
