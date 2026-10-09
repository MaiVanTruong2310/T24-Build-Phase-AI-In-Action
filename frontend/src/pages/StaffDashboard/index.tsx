import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchWithAuth } from '../../app/apiClient'
import { api, type Catalog } from '../../features/coordinator/api'

type Metrics = {
  cases_handled: number
  chat_escalations: number
  patients_total: number
  patients_new: number
  chat_cases_ai_handled_without_escalation: number
  cases_with_coordinator_intervention: number
  bookings_created: number
  bookings_approved: number
  schedules_starting: number
  reminders_delivered: number
}

type Summary = { range: { from: string; to: string }; metrics: Metrics }
type Option = { id: string; name: string }

const todayInVietnam = () => new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Ho_Chi_Minh' }).format(new Date())
const nextDate = (date: string) => {
  const value = new Date(`${date}T00:00:00+07:00`)
  value.setUTCDate(value.getUTCDate() + 1)
  return value.toISOString().slice(0, 10)
}

const cards: { key: keyof Metrics; title: string; href?: string }[] = [
  { key: 'patients_total', title: 'Bệnh nhân đang hoạt động', href: '/staff/patients' },
  { key: 'patients_new', title: 'Bệnh nhân mới trong kỳ', href: '/staff/patients' },
  { key: 'cases_handled', title: 'Ca điều phối đã hoàn tất', href: '/staff/queue' },
  { key: 'chat_escalations', title: 'Chatbot chuyển nhân viên', href: '/staff/chat' },
  { key: 'chat_cases_ai_handled_without_escalation', title: 'Ca chatbot hoàn tất không cần nhân viên can thiệp' },
  { key: 'cases_with_coordinator_intervention', title: 'Ca cần điều phối viên can thiệp', href: '/staff/queue' },
  { key: 'bookings_created', title: 'Booking được tạo', href: '/staff/booking-approvals' },
  { key: 'bookings_approved', title: 'Booking được duyệt', href: '/staff/booking-approvals' },
  { key: 'schedules_starting', title: 'Lịch bắt đầu trong kỳ', href: '/staff/doctor-schedule' },
  { key: 'reminders_delivered', title: 'Nhắc lịch đã gửi' },
]

export default function StaffDashboard() {
  const [from, setFrom] = useState(todayInVietnam)
  const [through, setThrough] = useState(todayInVietnam)
  const [facility, setFacility] = useState('')
  const [doctor, setDoctor] = useState('')
  const [facilities, setFacilities] = useState<Option[]>([])
  const [doctors, setDoctors] = useState<Option[]>([])
  const [summary, setSummary] = useState<Summary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    void api<Catalog>('/catalog').then((catalog) => {
      setFacilities(catalog.facilities)
      setDoctors(catalog.doctors)
    }).catch(() => {
      // Filters remain usable without catalog options; summary errors are shown separately.
    })
  }, [])

  const load = useCallback(async () => {
    if (!from || !through || from > through) {
      setSummary(null)
      setLoading(false)
      return
    }
    setLoading(true)
    setError('')
    const query = new URLSearchParams({
      from: `${from}T00:00:00+07:00`,
      to: `${nextDate(through)}T00:00:00+07:00`,
    })
    if (facility) query.set('facility_id', facility)
    if (doctor) query.set('doctor_id', doctor)
    try {
      const response = await fetchWithAuth(`/staff/dashboard/summary?${query}`)
      const body = await response.json()
      if (!response.ok) throw new Error(body.message || body.detail || 'Không thể tải tổng quan hệ thống.')
      setSummary(body.data as Summary)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Không thể tải tổng quan hệ thống.')
    } finally {
      setLoading(false)
    }
  }, [from, through, facility, doctor])

  useEffect(() => { void load() }, [load])

  const invalidRange = !from || !through || from > through
  return (
    <main className="mx-auto w-full max-w-7xl p-4 sm:p-6">
      <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Tổng quan vận hành</h1>
          <p className="mt-1 text-sm text-slate-600">Thống kê hệ thống theo dữ liệu đã ghi nhận.</p>
        </div>
        <Link to="/staff/queue" className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white">Mở hàng đợi điều phối</Link>
      </header>

      <section aria-label="Bộ lọc thống kê" className="mb-6 flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-white p-4">
        <label className="grid gap-1 text-sm font-medium text-slate-700">Từ ngày<input className="rounded-lg border border-slate-300 px-3 py-2" type="date" value={from} onChange={(event) => setFrom(event.target.value)} /></label>
        <label className="grid gap-1 text-sm font-medium text-slate-700">Đến ngày<input className="rounded-lg border border-slate-300 px-3 py-2" type="date" value={through} onChange={(event) => setThrough(event.target.value)} /></label>
        <label className="grid gap-1 text-sm font-medium text-slate-700">Cơ sở<select className="min-w-48 rounded-lg border border-slate-300 px-3 py-2" value={facility} onChange={(event) => setFacility(event.target.value)}><option value="">Tất cả cơ sở</option>{facilities.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        <label className="grid gap-1 text-sm font-medium text-slate-700">Bác sĩ<select className="min-w-48 rounded-lg border border-slate-300 px-3 py-2" value={doctor} onChange={(event) => setDoctor(event.target.value)}><option value="">Tất cả bác sĩ</option>{doctors.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
      </section>

      {invalidRange && <p role="alert" className="mb-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-800">Khoảng ngày không hợp lệ.</p>}
      {error && <div role="alert" className="mb-4 flex items-center justify-between gap-3 rounded-lg bg-rose-50 p-3 text-sm text-rose-800"><span>{error}</span><button className="font-semibold underline" onClick={() => void load()}>Thử lại</button></div>}
      {loading && <p role="status" className="mb-4 text-sm text-slate-600">Đang tải thống kê…</p>}
      {!loading && !error && summary && <>
        <p className="mb-3 text-sm text-slate-500">Khoảng thời gian: {new Date(summary.range.from).toLocaleDateString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' })} – {new Date(new Date(summary.range.to).getTime() - 1).toLocaleDateString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' })} (giờ Việt Nam)</p>
        <section aria-label="Chỉ số vận hành" className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {cards.map(({ key, title, href }) => {
            const value = summary.metrics[key].toLocaleString('vi-VN')
            const content = <><span className="text-sm font-medium text-slate-600">{title}</span><strong className="mt-3 text-3xl font-bold text-slate-900">{value}</strong></>
            return href ? <Link key={key} to={href} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm hover:border-emerald-300">{content}</Link> : <article key={key} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">{content}</article>
          })}
        </section>
        <p className="mt-5 text-xs text-slate-500">“AI hoàn tất không cần can thiệp” là chỉ số quy trình dựa trên sự kiện đã ghi nhận, không đánh giá độ chính xác lâm sàng.</p>
      </>}
    </main>
  )
}
