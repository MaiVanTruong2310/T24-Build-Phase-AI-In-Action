import { useCallback, useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, dateTime, priorities, statuses, type Case, type CaseDetail, type Catalog, type Dashboard, type Member, type Policy } from '../features/coordinator/api'
import './CoordinatorWorkbench.css'

const sourceNames: Record<string, string> = { chat: 'Hội thoại', consultation: 'Phiếu khám', package: 'Gói khám', booking: 'Lịch chờ duyệt' }
const eventNames: Record<string, string> = { claim: 'Nhận ca', handover: 'Bàn giao', takeover: 'Tiếp quản chat', resume: 'Trả về AI', contact: 'Liên hệ', follow_up: 'Hẹn liên hệ', emergency_detected: 'Phát hiện cảnh báo', emergency_ack: 'Tiếp nhận khẩn', emergency_transfer: 'Bàn giao cấp cứu', complete: 'Hoàn tất', cancel: 'Hủy', plan_updated: 'Đổi phương án khám', deposit_requested: 'Yêu cầu cọc', deposit_verified: 'Xác minh cọc', deposit_expired: 'Hết hạn cọc', booking_confirmed: 'Chốt lịch', refund_request: 'Yêu cầu hoàn cọc', refund_confirm: 'Xác nhận hoàn cọc', intake_submitted: 'Nhận phiếu', human_requested: 'Yêu cầu người hỗ trợ' }
const depositNames: Record<string, string> = { requested: 'Chờ chuyển cọc', verified: 'Đã xác minh', expired: 'Hết hạn', voided: 'Đã thay phương án', refund_pending: 'Chờ hoàn cọc', refunded: 'Đã hoàn cọc' }

export default function CoordinatorWorkbench({ mode = 'queue' }: { mode?: 'queue' | 'dashboard' | 'emergency' | 'chat' | 'settings' }) {
  const [params, setParams] = useSearchParams()
  const selectedId = params.get('case')
  const [me, setMe] = useState<Member | null>(null)
  const [members, setMembers] = useState<Member[]>([])
  const [items, setItems] = useState<Case[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [selected, setSelected] = useState<CaseDetail | null>(null)
  const [catalog, setCatalog] = useState<Catalog | null>(null)
  const [dashboard, setDashboard] = useState<Dashboard | null>(null)
  const [policy, setPolicy] = useState<Policy | null>(null)
  const [status, setStatus] = useState('')
  const [search, setSearch] = useState('')
  const [mine, setMine] = useState(false)
  const [error, setError] = useState('')
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

  const load = useCallback(async () => {
    const query = new URLSearchParams({ offset: String(offset), limit: '30' })
    if (status) query.set('status', status)
    if (search.trim()) query.set('q', search.trim())
    if (mine) query.set('mine', 'true')
    if (mode === 'emergency') query.set('priority', '0')
    if (mode === 'chat') query.set('conversations', 'true')
    const [list, stats] = await Promise.all([api<{ items: Case[]; total: number }>('/cases?' + query), api<Dashboard>('/dashboard')])
    setItems(list.items)
    setTotal(list.total); setDashboard(stats)
    setMembers(await api<Member[]>('/members'))
    const id = selectedRef.current
    if (id) { const value = await api<CaseDetail>('/cases/' + id); if (selectedRef.current === id) setSelected(value) }
    setLoading(false)
  }, [offset, status, search, mine, mode])
  useEffect(() => {
    let stopped = false
    void Promise.all([api<Member>('/me'), api<Member[]>('/members'), api<Catalog>('/catalog'), api<Policy | null>('/policy')]).then(([identity, people, options, p]) => {
      if (stopped) return
      setMe(identity); setMembers(people); setCatalog(options); setPolicy(p)
      if (p) setPolicyForm({ hold_minutes: String(p.hold_minutes), response_minutes: String(p.response_minutes), emergency_response_minutes: String(p.emergency_response_minutes), payment_instructions: p.payment_instructions, refund_policy: p.refund_policy })
    }).catch(e => { if (!stopped) { setError(e.message); setLoading(false) } })
    return () => { stopped = true }
  }, [])
  useEffect(() => {
    let stopped = false
    let timer: ReturnType<typeof setTimeout>
    const poll = async () => {
      if (!busyRef.current) try { await load(); if (!stopped) setError('') } catch (e) { if (!stopped) { setError(e instanceof Error ? e.message : 'Không thể tải dữ liệu.'); setLoading(false) } }
      if (!stopped) timer = setTimeout(poll, 5000)
    }
    void poll()
    return () => { stopped = true; clearTimeout(timer) }
  }, [load])
  useEffect(() => {
    setSelected(null); setNote(''); setMessage(''); setReference(''); setEvidence(''); setAgreed(false); setDoctor(''); setSpecialty(''); setService(''); setSchedule('')
    if (selectedId) void api<CaseDetail>('/cases/' + selectedId).then(value => { if (selectedRef.current === selectedId) setSelected(value) }).catch(e => setError(e.message))
  }, [selectedId])
  useEffect(() => {
    let stopped = false
    if (doctor) void api<Catalog>('/catalog?doctor_id=' + doctor).then(value => { if (!stopped) setCatalog(value) }).catch(e => setError(e.message))
    return () => { stopped = true }
  }, [doctor])
  const run = async (task: () => Promise<unknown>, success: string) => {
    busyRef.current = true; setBusy(true); setError(''); setNotice('')
    try { await task(); await load(); setNotice(success) } catch (e) { setError(e instanceof Error ? e.message : 'Thao tác thất bại.') }
    finally { busyRef.current = false; setBusy(false) }
  }
  const act = (action: string) => selected && run(() => api('/cases/' + selected.id + '/actions', 'POST', { version: selected.version, action, note, assigned_to: handover || null, follow_up_at: followUp ? new Date(followUp).toISOString() : null, reference: reference || null }), 'Đã lưu thao tác.')
  const owned = Boolean(selected && me && selected.assigned_to === me.user_id)
  const choose = (id: string) => setParams({ case: id })
  const person = (id: string | null) => members.find(x => x.user_id === id)?.name || (id ? 'Nhân viên đã ngừng hoạt động' : 'Chưa nhận')
  const title = mode === 'dashboard' ? 'Tổng quan điều phối' : mode === 'emergency' ? 'Ưu tiên cấp cứu' : mode === 'chat' ? 'Hội thoại cần hỗ trợ' : mode === 'settings' ? 'Tài khoản và chính sách' : 'Hàng đợi điều phối'
  return <div className="coordinator-workbench">
    <header className="cw-heading"><div><h1>{title}</h1><p>Điều hướng khám và hỗ trợ bệnh nhân. Không chẩn đoán xác định hoặc kê đơn.</p></div><button disabled={busy} onClick={() => void run(load, 'Đã cập nhật dữ liệu.')}>Làm mới</button></header>
    {error && <p className="cw-error" role="alert">{error}</p>}{notice && <p className="cw-notice" role="status">{notice}</p>}
    {loading && <p role="status">Đang tải dữ liệu…</p>}
    {me && <section className="cw-panel"><div className="cw-actions"><strong>{me.name} · {me.on_duty ? 'Đang trực' : 'Chưa bắt đầu ca trực'}</strong><button disabled={busy || me.on_duty} onClick={() => void run(async () => { await api('/duty/start', 'POST'); setMe(await api<Member>('/me')) }, 'Đã bắt đầu ca trực.')}>Bắt đầu ca trực</button><button disabled={busy || !me.on_duty} onClick={() => void run(async () => { await api('/duty/end', 'POST'); setMe(await api<Member>('/me')) }, 'Đã kết thúc ca trực.')}>Kết thúc ca trực</button></div><details><summary>Bàn giao toàn bộ ca đang xử lý và kết thúc ca trực</summary><label>Điều phối viên nhận ca<select value={handover} onChange={e => setHandover(e.target.value)}><option value="">Chọn người đang trực</option>{members.filter(m => m.user_id !== me.user_id && m.on_duty).map(m => <option key={m.user_id} value={m.user_id}>{m.name}</option>)}</select></label><label>Tóm tắt bàn giao<textarea value={note} onChange={e => setNote(e.target.value)} /></label><button disabled={busy || !handover || !note.trim()} onClick={() => void run(async () => { const result = await api<{ cases_transferred: number }>('/duty/handover', 'POST', { assigned_to: handover, note }); setMe(await api<Member>('/me')); setNotice(`Đã bàn giao ${result.cases_transferred} ca.`) }, 'Đã bàn giao ca trực.')}>Bàn giao và kết thúc ca trực</button></details></section>}
    {mode === 'settings' ? <div className="cw-columns"><section className="cw-panel"><h2>Chính sách vận hành</h2><p>Nhập điều khoản áp dụng thực tế. Chưa cấu hình sẽ không thể yêu cầu cọc.</p><form onSubmit={e => { e.preventDefault(); void run(async () => { const p = await api<Policy>('/policy', 'PUT', { ...policyForm, hold_minutes: Number(policyForm.hold_minutes), response_minutes: Number(policyForm.response_minutes), emergency_response_minutes: Number(policyForm.emergency_response_minutes) }); setPolicy(p) }, 'Đã lưu chính sách.') }}>
      <label>Thời hạn giữ chỗ (phút)<input type="number" min="5" max="1440" required value={policyForm.hold_minutes} onChange={e => setPolicyForm({ ...policyForm, hold_minutes: e.target.value })} /></label>
      <label>Hạn tiếp nhận thông thường (phút)<input type="number" min="1" required value={policyForm.response_minutes} onChange={e => setPolicyForm({ ...policyForm, response_minutes: e.target.value })} /></label>
      <label>Hạn tiếp nhận cấp cứu (phút)<input type="number" min="1" max="60" required value={policyForm.emergency_response_minutes} onChange={e => setPolicyForm({ ...policyForm, emergency_response_minutes: e.target.value })} /></label>
      <label>Hướng dẫn chuyển cọc<textarea required minLength={10} value={policyForm.payment_instructions} onChange={e => setPolicyForm({ ...policyForm, payment_instructions: e.target.value })} /></label><label>Điều kiện đổi/hủy/hoàn cọc<textarea required minLength={10} value={policyForm.refund_policy} onChange={e => setPolicyForm({ ...policyForm, refund_policy: e.target.value })} /></label><button className="cw-primary" disabled={busy || !me?.is_admin}>Lưu chính sách</button>
    </form></section><section className="cw-panel"><h2>Điều phối viên</h2><ul>{members.map(m => <li key={m.user_id}>{m.name} · {m.clinical_qualification}{m.is_admin ? ' · Quản trị' : ''}<small>{m.user_id}</small></li>)}</ul><form onSubmit={e => { e.preventDefault(); void run(async () => { await api('/members', 'PUT', { ...account, facility_ids: account.facility_ids.split(',').map(x => x.trim()).filter(Boolean) }); setMembers(await api<Member[]>('/members')) }, 'Đã lưu quyền tài khoản.') }}><label>ID tài khoản đã xác thực<input required value={account.user_id} onChange={e => setAccount({ ...account, user_id: e.target.value })} /></label><label>Thông tin chuyên môn<input required value={account.clinical_qualification} onChange={e => setAccount({ ...account, clinical_qualification: e.target.value })} /></label><label>ID cơ sở được phép (phân cách dấu phẩy; để trống nếu toàn hệ thống)<input value={account.facility_ids} onChange={e => setAccount({ ...account, facility_ids: e.target.value })} /></label><label className="cw-check"><input type="checkbox" checked={account.is_admin} onChange={e => setAccount({ ...account, is_admin: e.target.checked })} />Quản trị điều phối</label><label className="cw-check"><input type="checkbox" checked={account.enabled} onChange={e => setAccount({ ...account, enabled: e.target.checked })} />Cho phép hoạt động</label><button disabled={busy || !me?.is_admin}>Lưu quyền</button></form></section></div> : <>
      {dashboard && <section className="cw-stats"><div><span>Chưa nhận</span><strong>{dashboard.counts.new || 0}</strong></div><div><span>Cấp cứu đang mở</span><strong>{dashboard.emergency}</strong></div><div><span>Quá hạn xử lý</span><strong>{dashboard.overdue}</strong></div><div><span>Chờ cọc</span><strong>{dashboard.counts.waiting_deposit || 0}</strong></div></section>}
      {mode === 'dashboard' && dashboard && <section className="cw-panel"><h2>Nhắc việc đến hạn</h2>{dashboard.followups.length ? dashboard.followups.map(c => <button key={c.id} onClick={() => choose(c.id)}>{c.patient.name || 'Chưa có tên'} · {dateTime(c.follow_up_at)} · {person(c.assigned_to)}</button>) : <p>Không có nhắc việc đến hạn.</p>}</section>}
      <section className="cw-toolbar"><label>Tìm ca<input placeholder="Tên, điện thoại hoặc mã ca" value={search} onChange={e => { setSearch(e.target.value); setOffset(0) }} /></label><label>Trạng thái<select value={status} onChange={e => { setStatus(e.target.value); setOffset(0) }}><option value="">Tất cả</option>{Object.entries(statuses).filter(([k]) => k !== 'observing').map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label><label className="cw-check"><input type="checkbox" checked={mine} onChange={e => { setMine(e.target.checked); setOffset(0) }} />Ca của tôi</label></section>
      <div className={'cw-grid' + (selectedId ? ' cw-with-detail' : '')}><section className="cw-panel cw-queue"><div className="cw-table-wrap"><table><thead><tr><th>Bệnh nhân / mã</th><th>Ưu tiên</th><th>Trạng thái</th><th>Phụ trách</th><th>Tạo lúc</th></tr></thead><tbody>{items.map(c => <tr key={c.id} className={c.id === selectedId ? 'cw-selected' : ''}><td><button onClick={() => choose(c.id)} className="cw-link">{c.patient.name || 'Chưa có tên'}</button><small>{c.patient.phone || 'Chưa có điện thoại'} · {sourceNames[c.source] || c.source}</small><small>{c.id.slice(0, 8).toUpperCase()}</small></td><td className={c.priority === 0 ? 'cw-critical' : ''}>{priorities[c.priority]}</td><td>{statuses[c.status] || c.status}</td><td>{person(c.assigned_to)}</td><td>{dateTime(c.created_at)}</td></tr>)}</tbody></table></div>{!loading && !items.length && <p className="cw-empty">Không có ca phù hợp.</p>}<footer className="cw-pagination"><span>{total} ca</span><button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 30))}>Trước</button><button disabled={offset + 30 >= total} onClick={() => setOffset(offset + 30)}>Sau</button></footer></section>
      {selectedId && <aside className="cw-detail"><button onClick={() => setParams({})}>Đóng hồ sơ</button>{!selected ? <p>Đang tải hồ sơ…</p> : <>
        <section className="cw-panel"><h2>{selected.patient.name || 'Hồ sơ ca'}</h2><small>Mã {selected.id} · phiên bản {selected.version}</small><p>{statuses[selected.status]} · {priorities[selected.priority]} · {person(selected.assigned_to)}</p><dl>{Object.entries(selected.patient).filter(([, v]) => v).map(([k, v]) => <div key={k}><dt>{{ name: 'Họ tên', phone: 'Điện thoại', email: 'Email', date_of_birth: 'Ngày sinh', gender: 'Giới tính', guardian_name: 'Người giám hộ', guardian_phone: 'Liên hệ giám hộ', preferred_date: 'Ngày mong muốn', preferred_period: 'Buổi mong muốn', facility_preference: 'Cơ sở mong muốn', contact_time_preference: 'Thời gian liên hệ', notes: 'Nội dung yêu cầu', consent_to_contact: 'Đồng ý liên hệ' }[k] || k}</dt><dd>{String(v)}</dd></div>)}</dl><p>Hạn xử lý: {dateTime(selected.due_at)}. Nhắc việc: {dateTime(selected.follow_up_at)}</p><button disabled={busy || Boolean(selected.assigned_to && !owned)} onClick={() => void act('claim')}>Nhận ca</button></section>
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
              {(selected.ai_snapshot.care_pipeline as any)?.pipeline_steps?.length ? (
                <div className="cw-pipeline-container">
                  <div className="cw-pipeline-header">
                    <strong>🏥 Lộ trình Khám Ưu tiên Phân tầng (Staged Care Navigation):</strong>
                    <small>Nguyên tắc y khoa: Cơ quan sinh tồn luôn được ưu tiên khám trước mức độ đau đơn thuần.</small>
                  </div>
                  <div className="cw-pipeline-steps">
                    {((selected.ai_snapshot.care_pipeline as any).pipeline_steps as any[]).map((step: any) => (
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
        <section className="cw-panel"><h2>Liên hệ và bàn giao</h2><label>Kết quả liên hệ / lý do thao tác<textarea value={note} onChange={e => setNote(e.target.value)} /></label><div className="cw-actions"><button disabled={busy || !owned || !note.trim()} onClick={() => void act('contact')}>Lưu kết quả liên hệ</button><button disabled={busy || !owned || !note.trim()} onClick={() => void act('complete')}>Hoàn tất ca</button><button disabled={busy || !owned || !note.trim()} onClick={() => void act('cancel')}>Hủy ca</button></div><label>Nhắc liên hệ lúc<input type="datetime-local" value={followUp} onChange={e => setFollowUp(e.target.value)} /></label><button disabled={busy || !owned || !followUp} onClick={() => void act('follow_up')}>Đặt nhắc việc</button><label>Người nhận bàn giao<select value={handover} onChange={e => setHandover(e.target.value)}><option value="">Chọn điều phối viên</option>{members.filter(m => m.user_id !== me?.user_id).map(m => <option key={m.user_id} value={m.user_id}>{m.name}</option>)}</select></label><button disabled={busy || !owned || !handover || !note.trim()} onClick={() => void act('handover')}>Bàn giao ca</button>{selected.priority === 0 && <div className="cw-emergency"><h3>Xử lý cấp cứu</h3><p>Ghi diễn biến và đơn vị tiếp nhận thực tế trong phần ghi chú.</p><button disabled={busy || !owned || !note.trim()} onClick={() => void act('emergency_ack')}>Ghi nhận tiếp nhận khẩn</button><button disabled={busy || !owned || !note.trim()} onClick={() => void act('emergency_transfer')}>Ghi nhận bàn giao cấp cứu</button></div>}</section>
        {selected.session_id && <section className="cw-panel"><h2>Hội thoại</h2><p>{selected.control === 'human' ? 'Bác sĩ điều phối đang trả lời; AI tạm dừng.' : 'AI đang trả lời.'}</p><div className="cw-actions"><button disabled={busy || !owned || selected.control === 'human'} onClick={() => void act('takeover')}>Tiếp quản</button><button disabled={busy || !owned || selected.control !== 'human' || !note.trim()} onClick={() => void act('resume')}>Trả về AI kèm tóm tắt</button></div><div className="cw-messages">{selected.messages.map(m => <article key={m.id}><strong>{m.sender === 'patient' ? 'Bệnh nhân' : m.sender === 'coordinator' ? person(m.actor_id) : m.sender === 'ai' ? 'AI' : 'Thông báo'}</strong><time>{dateTime(m.created_at)}</time><p>{m.body}</p></article>)}</div><form onSubmit={e => { e.preventDefault(); const body = message; void run(async () => { await api('/cases/' + selected.id + '/messages', 'POST', { client_id: crypto.randomUUID(), body }); setMessage('') }, 'Đã gửi tin nhắn.') }}><label>Tư vấn điều hướng<textarea required value={message} onChange={e => setMessage(e.target.value)} placeholder="Hỏi rõ triệu chứng, giải thích chuyên khoa hoặc hướng dẫn bước tiếp theo." /></label><button className="cw-primary" disabled={busy || !owned || selected.control !== 'human' || !message.trim()}>Gửi tới bệnh nhân</button></form></section>}
        {selected.priority !== 0 && <section className="cw-panel"><h2>Phương án khám</h2>{selected.plan.starts_at && <p>Phương án hiện tại: {dateTime(String(selected.plan.starts_at))} · {catalog?.doctors.find(d => d.id === selected.plan.doctor_id)?.name || 'Bác sĩ đã chọn'}</p>}<form onSubmit={e => { e.preventDefault(); void run(() => api('/cases/' + selected.id + '/plan', 'PUT', { version: selected.version, specialty_id: specialty, service_id: service, schedule_id: schedule, reason: note, patient_agreed: agreed }), 'Đã lưu phương án khám.') }}><label>Chuyên khoa<select required value={specialty} onChange={e => setSpecialty(e.target.value)}><option value="">Chọn chuyên khoa</option>{catalog?.specialties.map(x => <option key={x.id} value={x.id}>{x.name}</option>)}</select></label><label>Dịch vụ<select required value={service} onChange={e => setService(e.target.value)}><option value="">Chọn dịch vụ</option>{catalog?.services.map(x => <option key={x.id} value={x.id}>{x.name}</option>)}</select></label><label>Bác sĩ<select required value={doctor} onChange={e => { setDoctor(e.target.value); setSchedule('') }}><option value="">Chọn bác sĩ</option>{catalog?.doctors.map(x => <option key={x.id} value={x.id}>{x.name}</option>)}</select></label><label>Giờ và cơ sở<select required value={schedule} onChange={e => setSchedule(e.target.value)}><option value="">Chọn lịch đã công bố</option>{catalog?.schedules.map(x => <option key={x.id} value={x.id}>{dateTime(x.starts_at)} · {catalog.facilities.find(f => f.id === x.facility_id)?.name || 'Cơ sở'}</option>)}</select></label><label className="cw-check"><input type="checkbox" checked={agreed} onChange={e => setAgreed(e.target.checked)} />Bệnh nhân đã đồng ý phương án và điều khoản áp dụng</label><p>Lý do điều chỉnh lấy từ phần ghi chú xử lý ở trên. Lưu phương án chưa giữ chỗ.</p><button disabled={busy || !owned || !agreed || !note.trim()}>Lưu phương án / đổi lịch</button></form></section>}
        {selected.priority !== 0 && <section className="cw-panel"><h2>Cọc và xác nhận lịch</h2><p>Xác minh thủ công trên giao dịch thực tế. Không tự động thu hoặc hoàn tiền.</p>{!policy && <p>Chưa cấu hình điều khoản cọc.</p>}{selected.deposits.map(d => <article className="cw-deposit" key={d.id}><strong>{d.amount.toLocaleString('vi-VN')} {d.currency} · {depositNames[d.status] || d.status}</strong><p>Hạn: {dateTime(d.expires_at)}</p><p>{d.instructions}</p><p>Hoàn cọc: {d.refund_policy}</p>{d.transaction_reference && <p>Mã giao dịch: {d.transaction_reference}</p>}</article>)}<form onSubmit={e => { e.preventDefault(); void run(() => api('/cases/' + selected.id + '/deposits', 'POST', { version: selected.version, amount: Number(amount) }), 'Đã giữ chỗ và gửi yêu cầu cọc.') }}><label>Số tiền cọc (VND)<input type="number" required min="1" value={amount} onChange={e => setAmount(e.target.value)} /></label><button disabled={busy || !owned || !policy || selected.status !== 'planned'}>Giữ chỗ và yêu cầu cọc</button></form><label>Mã giao dịch chuyển/hoàn cọc<input value={reference} onChange={e => setReference(e.target.value)} /></label><label>Bằng chứng đã đối soát<textarea value={evidence} onChange={e => setEvidence(e.target.value)} placeholder="Thông tin giao dịch từ nguồn thanh toán đã kiểm tra." /></label><div className="cw-actions"><button disabled={busy || !owned || !reference.trim() || !evidence.trim()} onClick={() => void run(() => api('/cases/' + selected.id + '/verify-deposit', 'POST', { version: selected.version, reference, evidence }), 'Đã xác minh khoản cọc.')}>Xác minh cọc</button><button className="cw-primary" disabled={busy || !owned || !['deposit_verified', 'waiting_deposit'].includes(selected.status)} onClick={() => void run(() => api('/cases/' + selected.id + '/confirm', 'POST', { version: selected.version }), 'Đã chốt lịch và lưu thông báo.')}>Chốt lịch</button><button disabled={busy || !owned || !note.trim()} onClick={() => void act('refund_request')}>Yêu cầu hoàn cọc</button><button disabled={busy || !owned || !note.trim() || !reference.trim()} onClick={() => void act('refund_confirm')}>Xác nhận đã hoàn cọc</button></div></section>}
        <section className="cw-panel"><h2>Lịch sử thao tác</h2>{selected.events.length ? selected.events.map(e => <article key={e.id} className="cw-event"><strong>{eventNames[e.action] || e.action}</strong><small>{dateTime(e.created_at)} · {person(e.actor_id)}</small>{e.note && <p>{e.note}</p>}</article>) : <p>Chưa có thao tác.</p>}</section>
      </>}</aside>}
      </div>
    </>}
  </div>
}
