import { useCallback, useEffect, useState } from 'react'
import { fetchDoctors, fetchFacilities } from '../features/appointment-booking/api'
import type { Doctor, Facility } from '../features/appointment-booking/api'
import {
  assignConsultation, createStandardWeek, createWeeklyShift, fetchCoordinatorRequests, fetchWeeklyShifts,
  publishSessions, rejectConsultation,
} from '../features/coordination/api'
import type { ConsultationRequest } from '../features/coordination/api'

const localDate = (value: Date) => `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`
const today = () => localDate(new Date())
const inFourWeeks = () => localDate(new Date(Date.now() + 27 * 86400000))
const weekdays = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ nhật']
const displayTime = (value: string) => new Date(value).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })

export default function CoordinatorSchedule() {
  const [doctors, setDoctors] = useState<Doctor[]>([])
  const [facilities, setFacilities] = useState<Facility[]>([])
  const [rules, setRules] = useState<Awaited<ReturnType<typeof fetchWeeklyShifts>>>([])
  const [requests, setRequests] = useState<ConsultationRequest[]>([])
  const [doctorId, setDoctorId] = useState('')
  const [facilityId, setFacilityId] = useState('')
  const [weekday, setWeekday] = useState(0)
  const [period, setPeriod] = useState<'morning' | 'afternoon'>('morning')
  const [startTime, setStartTime] = useState('08:00')
  const [slotMinutes, setSlotMinutes] = useState(30)
  const [slotCount, setSlotCount] = useState(5)
  const [fromDate, setFromDate] = useState(today)
  const [throughDate, setThroughDate] = useState(inFourWeeks)
  const [selections, setSelections] = useState<Record<string, string>>({})
  const [notes, setNotes] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const reload = useCallback(async () => {
    const [nextRules, nextRequests] = await Promise.all([fetchWeeklyShifts(), fetchCoordinatorRequests()])
    setRules(nextRules); setRequests(nextRequests)
  }, [])
  useEffect(() => {
    void Promise.all([fetchDoctors({ professionalRole: 'Bác sĩ', bookingEnabled: true }), fetchFacilities()]).then(([d, f]) => {
      setDoctors(d); setFacilities(f)
    }).catch(() => setError('Không thể tải danh mục bác sĩ hoặc cơ sở.'))
    void reload().catch(cause => setError(cause instanceof Error ? cause.message : 'Không thể tải dữ liệu điều phối.'))
  }, [reload])

  const run = async (task: () => Promise<unknown>, success: string) => {
    setBusy(true); setError(''); setNotice('')
    try { await task(); await reload(); setNotice(success) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Không thể hoàn thành thao tác.') }
    finally { setBusy(false) }
  }
  const addRule = () => void run(() => createWeeklyShift({ doctor_id: doctorId, facility_id: facilityId,
    weekday, period, start_time: startTime, slot_minutes: slotMinutes, slot_count: slotCount,
    effective_from: fromDate }), 'Đã lưu quy tắc lịch tuần.')
  const publish = () => void run(async () => {
    const value = await publishSessions(fromDate, throughDate)
    setNotice(`Đã công bố ${value.sessions_created} buổi khám.`)
  }, 'Đã cập nhật lịch khám.')

  return <div className="space-y-6 p-4 md:p-7">
    <header className="rounded-2xl bg-gradient-to-r from-slate-950 to-blue-900 p-6 text-white"><p className="text-xs uppercase tracking-wider text-blue-200">VCare+ · Nhân viên</p><h1 className="mt-2 text-2xl font-bold">Điều phối lịch khám</h1><p className="mt-2 text-sm text-blue-100">Công bố 5 giờ khám nội bộ mỗi buổi, gọi lại và chốt giờ với từng bệnh nhân.</p></header>
    {error && <p role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</p>}
    {notice && <p role="status" className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">{notice}</p>}
    <section className="rounded-2xl border bg-white p-5 shadow-sm"><h2 className="text-lg font-bold">Quy tắc làm việc hằng tuần</h2><p className="mt-1 text-sm text-slate-500">Tạo riêng ca sáng và chiều cho từng ngày bác sĩ làm việc. Mặc định 5 lượt mỗi ca.</p>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <label className="text-sm">Bác sĩ<select value={doctorId} onChange={e => setDoctorId(e.target.value)} className="mt-1 w-full rounded-lg border p-2"><option value="">Chọn bác sĩ</option>{doctors.map(x => <option key={x.id} value={x.id}>{x.full_name}</option>)}</select></label>
        <label className="text-sm">Cơ sở<select value={facilityId} onChange={e => setFacilityId(e.target.value)} className="mt-1 w-full rounded-lg border p-2"><option value="">Chọn cơ sở</option>{facilities.map(x => <option key={x.id} value={x.id}>{x.name}</option>)}</select></label>
        <label className="text-sm">Ngày trong tuần<select value={weekday} onChange={e => setWeekday(Number(e.target.value))} className="mt-1 w-full rounded-lg border p-2">{weekdays.map((x, i) => <option key={i} value={i}>{x}</option>)}</select></label>
        <label className="text-sm">Buổi<select value={period} onChange={e => { const value = e.target.value as 'morning' | 'afternoon'; setPeriod(value); setStartTime(value === 'morning' ? '08:00' : '13:30') }} className="mt-1 w-full rounded-lg border p-2"><option value="morning">Sáng</option><option value="afternoon">Chiều</option></select></label>
        <label className="text-sm">Giờ bắt đầu<input type="time" value={startTime} onChange={e => setStartTime(e.target.value)} className="mt-1 w-full rounded-lg border p-2" /></label>
        <label className="text-sm">Phút mỗi slot<input type="number" min={5} max={240} value={slotMinutes} onChange={e => setSlotMinutes(Number(e.target.value))} className="mt-1 w-full rounded-lg border p-2" /></label>
        <label className="text-sm">Số slot<input type="number" min={1} max={20} value={slotCount} onChange={e => setSlotCount(Number(e.target.value))} className="mt-1 w-full rounded-lg border p-2" /></label>
        <label className="text-sm">Có hiệu lực từ<input type="date" min={today()} value={fromDate} onChange={e => setFromDate(e.target.value)} className="mt-1 w-full rounded-lg border p-2" /></label>
      </div>
      <button disabled={busy || !doctorId || !facilityId} onClick={addRule} className="mt-4 rounded-lg bg-blue-700 px-5 py-2 text-sm font-semibold text-white disabled:opacity-50">Lưu quy tắc</button>
      <button disabled={busy || !doctorId || !facilityId} onClick={() => void run(() => createStandardWeek(doctorId, facilityId, fromDate), 'Đã tạo lịch thứ 2 đến chủ nhật, sáng và chiều.')} className="ml-2 mt-4 rounded-lg border border-blue-300 px-5 py-2 text-sm font-semibold text-blue-800 disabled:opacity-50">Tạo cả tuần · 5 slot/buổi</button>
      <div className="mt-4 flex flex-wrap gap-2">{rules.map(x => <span key={x.id} className="rounded-full border bg-slate-50 px-3 py-1 text-xs">{doctors.find(d => d.id === x.doctor_id)?.full_name || x.doctor_id} · {weekdays[x.weekday]} · {x.period === 'morning' ? 'Sáng' : 'Chiều'} {x.start_time.slice(0, 5)} · {x.slot_count} slot</span>)}</div>
    </section>
    <section className="rounded-2xl border bg-white p-5 shadow-sm"><h2 className="text-lg font-bold">Công bố ca khám theo ngày</h2><p className="mt-1 text-sm text-slate-500">Tạo các slot từ quy tắc tuần, tối đa 43 ngày một lần. Lần công bố lại không tạo trùng.</p><div className="mt-4 flex flex-wrap items-end gap-3"><label className="text-sm">Từ ngày<input type="date" value={fromDate} onChange={e => setFromDate(e.target.value)} className="mt-1 block rounded-lg border p-2" /></label><label className="text-sm">Đến ngày<input type="date" value={throughDate} onChange={e => setThroughDate(e.target.value)} className="mt-1 block rounded-lg border p-2" /></label><button disabled={busy || rules.length === 0} onClick={publish} className="rounded-lg bg-slate-900 px-5 py-2 text-sm font-semibold text-white disabled:opacity-50">Công bố lịch</button></div></section>
    <section className="rounded-2xl border bg-white p-5 shadow-sm"><div className="flex items-center justify-between"><h2 className="text-lg font-bold">Yêu cầu cần gọi lại</h2><button onClick={() => void reload()} className="text-sm font-semibold text-blue-700">Làm mới</button></div><p className="mt-1 text-sm text-slate-500">Chỉ nhân viên nhìn thấy giờ cụ thể. Hãy gọi bệnh nhân trước khi xác nhận slot.</p>
      <div className="mt-4 grid gap-4 xl:grid-cols-2">{requests.filter(x => x.status === 'pending').map(item => <article key={item.id} className="rounded-2xl border border-amber-200 bg-amber-50/40 p-4"><div className="flex flex-wrap items-start justify-between gap-2"><div><h3 className="font-bold">{item.patient_name || 'Bệnh nhân'} · {item.date} {item.period === 'morning' ? 'sáng' : 'chiều'}</h3><p className="mt-1 text-sm text-slate-600">{item.patient_phone || item.patient_email || 'Chưa có liên hệ'}</p></div><span className="rounded-full bg-amber-100 px-2 py-1 text-xs font-semibold text-amber-800">Chờ gọi lại</span></div><p className="mt-2 text-sm text-slate-600">{item.doctor_name} · {item.facility_name} · {item.specialty_name} · {item.service_name}</p><p className="mt-3 text-sm"><strong>Lý do:</strong> {item.reason}</p><label className="mt-3 block text-sm font-medium">Chọn giờ sau khi tư vấn<select className="mt-1 w-full rounded-lg border bg-white p-2" value={selections[item.id] || ''} onChange={e => setSelections(s => ({ ...s, [item.id]: e.target.value }))}><option value="">Chọn slot còn trống</option>{item.slots?.filter(slot => slot.available).map(slot => <option key={slot.id} value={slot.id}>{displayTime(slot.starts_at)} – {displayTime(slot.ends_at)}</option>)}</select></label><label className="mt-3 block text-sm font-medium">Ghi chú cuộc gọi<input className="mt-1 w-full rounded-lg border p-2" value={notes[item.id] || ''} onChange={e => setNotes(s => ({ ...s, [item.id]: e.target.value }))} /></label><div className="mt-4 flex flex-wrap gap-2"><button disabled={busy || !selections[item.id]} onClick={() => void run(() => assignConsultation(item.id, selections[item.id], notes[item.id] || ''), 'Đã xác nhận giờ khám.')} className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">Chốt giờ khám</button><button disabled={busy} onClick={() => { const note = notes[item.id]?.trim() || window.prompt('Lý do từ chối yêu cầu:')?.trim(); if (note) void run(() => rejectConsultation(item.id, note), 'Đã đóng yêu cầu.') }} className="rounded-lg border border-red-200 px-4 py-2 text-sm font-semibold text-red-700 disabled:opacity-50">Không thể nhận</button></div></article>)}</div>
      {requests.every(x => x.status !== 'pending') && <p className="mt-5 rounded-xl bg-slate-50 p-5 text-sm text-slate-500">Không có yêu cầu chờ điều phối.</p>}
    </section>
    <section className="rounded-2xl border bg-white p-5 shadow-sm"><h2 className="font-bold">Lịch sử xử lý</h2><div className="mt-3 space-y-2">{requests.filter(x => x.status !== 'pending').slice(0, 20).map(x => <div key={x.id} className="flex flex-wrap justify-between gap-2 rounded-xl border p-3 text-sm"><span>{x.patient_name || 'Bệnh nhân'} · {x.date} · {x.period === 'morning' ? 'Sáng' : 'Chiều'}</span><span className={x.status === 'confirmed' ? 'text-emerald-700' : 'text-red-700'}>{x.status === 'confirmed' ? `Đã chốt ${x.starts_at ? displayTime(x.starts_at) : ''}` : 'Đã từ chối'}</span></div>)}</div></section>
  </div>
}
