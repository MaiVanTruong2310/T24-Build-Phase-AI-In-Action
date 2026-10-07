import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchWeeklyShifts, createWeeklyShift, publishSessions } from '../features/coordination/api'
import { api, type Catalog } from '../features/coordinator/api'
import { saveAndRefresh } from '../features/coordinator/mutations'
import { publicationError, shiftError } from '../features/coordinator/uiLogic'
import { formatDateVN } from '../features/appointment-booking/dateValidation'
import { DateInputVN } from '../components/DateInputVN'
import { Link } from 'react-router-dom'
import './CoordinatorWorkbench.css'

const weekdays = ['Thứ hai', 'Thứ ba', 'Thứ tư', 'Thứ năm', 'Thứ sáu', 'Thứ bảy', 'Chủ nhật']
function todayIso() { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}` }

export default function CoordinatorSchedule() {
  const [catalog, setCatalog] = useState<Catalog | null>(null)
  const [facilities, setFacilities] = useState<Catalog['facilities']>([])
  const [optionsBusy, setOptionsBusy] = useState(false)
  const [rules, setRules] = useState<Awaited<ReturnType<typeof fetchWeeklyShifts>>>([])
  const [form, setForm] = useState({ doctor_id: '', facility_id: '', weekday: '0', period: 'morning', start_time: '', slot_minutes: '', slot_count: '', effective_from: '' })
  const [from, setFrom] = useState('')
  const [through, setThrough] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const busyRef = useRef(false)
  const active = useRef(true)
  const load = useCallback(async () => {
    const [options, shifts] = await Promise.all([api<Catalog>('/catalog'), fetchWeeklyShifts()])
    if (active.current) { setCatalog(options); setRules(shifts) }
  }, [])
  useEffect(() => { active.current = true; void load().catch(e => { if (active.current) setError(e.message) }); return () => { active.current = false } }, [load])
  useEffect(() => {
    let current = true
    setFacilities([]); setOptionsBusy(Boolean(form.doctor_id))
    if (form.doctor_id) void api<Catalog>('/catalog?doctor_id=' + form.doctor_id).then(value => {
      if (current) setFacilities(value.facilities)
    }).catch(e => { if (current) setError(e.message) }).finally(() => { if (current) setOptionsBusy(false) })
    return () => { current = false }
  }, [form.doctor_id])
  const run = async (task: () => Promise<string>) => {
    if (busyRef.current) return
    busyRef.current = true; setBusy(true); setError(''); setNotice('')
    try {
      const outcome = await saveAndRefresh(task, result => { if (active.current) setNotice(result) }, load)
      if (active.current && !outcome.refreshed) setError('Đã lưu lịch thành công nhưng chưa tải lại được dữ liệu. Hãy làm mới.')
    } catch (e) { if (active.current) setError(e instanceof Error ? e.message : 'Không thể lưu lịch.') }
    finally { busyRef.current = false; if (active.current) setBusy(false) }
  }
  return <div className="coordinator-workbench">
    <header className="cw-heading"><div><h1>Công bố lịch khám</h1><p>Nhập ca làm việc thực tế. Lịch đã công bố được sử dụng khi điều phối và giữ chỗ.</p></div><Link to="/staff/queue">Mở hàng đợi</Link><button disabled={busy} onClick={() => void load().then(() => setError('')).catch(e => setError(e.message))}>Làm mới</button></header>
    {error && <p className="cw-error" role="alert">{error}</p>}{notice && <p className="cw-notice" role="status">{notice}</p>}
    <section className="cw-panel"><h2>Quy tắc lịch tuần</h2><form onSubmit={e => {
      e.preventDefault()
      const validation = shiftError(form)
      if (validation) { setError(validation); return }
      if (!facilities.some(x => x.id === form.facility_id)) { setError('Chọn cơ sở thuộc bác sĩ đã chọn.'); return }
      void run(async () => { await createWeeklyShift({ ...form, weekday: Number(form.weekday), slot_minutes: Number(form.slot_minutes), slot_count: Number(form.slot_count) }); return 'Đã lưu quy tắc lịch tuần.' })
    }}><fieldset disabled={busy}><div className="cw-columns"><div>
      <label>Bác sĩ<select required value={form.doctor_id} onChange={e => setForm({ ...form, doctor_id: e.target.value, facility_id: '' })}><option value="">Chọn bác sĩ</option>{catalog?.doctors.map(x => <option key={x.id} value={x.id}>{x.name}</option>)}</select></label>
      <label>Cơ sở<select required disabled={!form.doctor_id || optionsBusy} value={form.facility_id} onChange={e => setForm({ ...form, facility_id: e.target.value })}><option value="">{optionsBusy ? 'Đang tải cơ sở…' : 'Chọn cơ sở'}</option>{facilities.map(x => <option key={x.id} value={x.id}>{x.name}</option>)}</select></label>
      <label>Ngày làm việc<select value={form.weekday} onChange={e => setForm({ ...form, weekday: e.target.value })}>{weekdays.map((x, i) => <option key={i} value={i}>{x}</option>)}</select></label>
      <label>Buổi<select value={form.period} onChange={e => setForm({ ...form, period: e.target.value, start_time: '' })}><option value="morning">Sáng</option><option value="afternoon">Chiều</option></select></label>
    </div><div>
      <label>Giờ bắt đầu<input required type="time" min={form.period === 'morning' ? '00:00' : '12:00'} max={form.period === 'morning' ? '11:59' : '23:59'} value={form.start_time} onChange={e => setForm({ ...form, start_time: e.target.value })} /></label>
      <label>Thời lượng mỗi lượt (phút)<input required type="number" min="5" max="240" value={form.slot_minutes} onChange={e => setForm({ ...form, slot_minutes: e.target.value })} /></label>
      <label>Số lượt khám mỗi buổi<input required type="number" min="1" max="20" value={form.slot_count} onChange={e => setForm({ ...form, slot_count: e.target.value })} /></label>
      <label>Có hiệu lực từ (dd/mm/yyyy)<DateInputVN required value={form.effective_from} onChange={e => setForm({ ...form, effective_from: e.target.value })} /></label>
    </div></div><button disabled={optionsBusy || !catalog}>Lưu quy tắc</button></fieldset></form>
    <table><thead><tr><th>Bác sĩ</th><th>Cơ sở</th><th>Ngày / buổi</th><th>Giờ</th><th>Số lượt</th></tr></thead><tbody>{rules.map(x => <tr key={x.id}><td>{catalog?.doctors.find(d => d.id === x.doctor_id)?.name || x.doctor_id}</td><td>{catalog?.facilities.find(f => f.id === x.facility_id)?.name || x.facility_id}</td><td>{weekdays[x.weekday]} · {x.period === 'morning' ? 'Sáng' : 'Chiều'}</td><td>{x.start_time.slice(0, 5)}</td><td>{x.slot_count}</td></tr>)}</tbody></table>{!rules.length && <p>Chưa có quy tắc lịch.</p>}</section>
    <section className="cw-panel"><h2>Công bố lịch theo ngày</h2><form onSubmit={e => {
      e.preventDefault()
      const validation = publicationError(from, through, todayIso())
      if (validation) { setError(validation); return }
      void run(async () => { const result = await publishSessions(from, through); return `Đã tạo ${result.sessions_created} buổi khám.` })
    }}><fieldset disabled={busy}><div className="cw-columns"><label>Từ ngày (dd/mm/yyyy)<DateInputVN required min={todayIso()} value={from} onChange={e => setFrom(e.target.value)} /></label><label>Đến ngày (dd/mm/yyyy)<DateInputVN required min={from || todayIso()} value={through} onChange={e => setThrough(e.target.value)} /></label></div><button disabled={!rules.some(rule => rule.active)}>Công bố lịch</button></fieldset></form></section>
  </div>
}
