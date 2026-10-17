import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Activity, CalendarCheck2, CalendarClock, ClipboardCheck, UsersRound, BellRing } from 'lucide-react'
import { useDispatch, useSelector } from 'react-redux'
import type { AppDispatch, RootState } from '../../app/store'
import { loadDashboardDoctors, loadDashboardFacilities, loadDashboardSummary, selectDashboardSummary, selectDashboardSummaryError, selectDashboardSummaryLoading, setDashboardFilter, type DashboardMetrics as Metrics } from '../../features/staff-dashboard/staffDashboardSlice'
import { DataLoadingState } from '../../components/DataLoadingState'

const number = (value: number) => value.toLocaleString('vi-VN')

const cards: { key: keyof Metrics; title: string; href: string; icon: typeof UsersRound; tone: string }[] = [
  { key: 'patients_total', title: 'Bệnh nhân đang hoạt động toàn hệ thống', href: '/staff/patients', icon: UsersRound, tone: 'sky' },
  { key: 'cases_handled', title: 'Ca điều phối đã hoàn tất', href: '/staff/queue', icon: ClipboardCheck, tone: 'emerald' },
  { key: 'bookings_approved', title: 'Booking được duyệt', href: '/staff/booking-approvals', icon: CalendarCheck2, tone: 'violet' },
  { key: 'cases_with_coordinator_intervention', title: 'Ca có điều phối viên can thiệp', href: '/staff/queue', icon: Activity, tone: 'amber' },
  { key: 'schedules_starting', title: 'Lịch khám bắt đầu trong kỳ', href: '/staff/doctor-schedule', icon: CalendarClock, tone: 'cyan' },
  { key: 'reminders_delivered', title: 'Nhắc lịch đã gửi', href: '/staff/booking-approvals', icon: BellRing, tone: 'rose' },
]
const iconTone: Record<string, string> = {
  sky: 'bg-sky-50 text-sky-700',
  emerald: 'bg-emerald-50 text-emerald-700',
  violet: 'bg-violet-50 text-violet-700',
  amber: 'bg-amber-50 text-amber-700',
  cyan: 'bg-cyan-50 text-cyan-700',
  rose: 'bg-rose-50 text-rose-700',
}

export default function StaffDashboard() {
  const dispatch = useDispatch<AppDispatch>()
  const { filters, facilities, facilityLoading, facilityError, doctors, doctorsLoading, doctorsError } = useSelector((state: RootState) => state.staffDashboard)
  const { from, through, facility, doctor } = filters
  const summary = useSelector(selectDashboardSummary)
  const loading = useSelector(selectDashboardSummaryLoading)
  const error = useSelector(selectDashboardSummaryError)
  const optionsLoading = facilityLoading || (doctorsLoading[facility] ?? false)
  const optionsError = facilityError || doctorsError[facility] || ''
  const doctorsForFacility = doctors[facility] ?? []

  useEffect(() => { void dispatch(loadDashboardFacilities()); void dispatch(loadDashboardDoctors({ facility })) }, [dispatch, facility])
  useEffect(() => { if (from && through && from <= through) void dispatch(loadDashboardSummary({ filters })) }, [dispatch, filters, from, through, facility, doctor])
  const change = (key: 'from' | 'through' | 'facility' | 'doctor', value: string) => dispatch(setDashboardFilter({ key, value }))
  const retryOptions = () => { void dispatch(loadDashboardFacilities({ force: true })); void dispatch(loadDashboardDoctors({ facility, force: true })) }
  const retrySummary = () => { void dispatch(loadDashboardSummary({ filters, force: true })) }
  const invalidRange = !from || !through || from > through
  return (
    <main className="mx-auto w-full max-w-7xl space-y-6 p-4 sm:p-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-emerald-700">Trung tâm điều phối</p>
          <h1 className="mt-1 text-2xl font-bold text-slate-900">Tổng quan vận hành</h1>
          <p className="mt-1 text-sm text-slate-600">Các chỉ số được tổng hợp từ hoạt động đã ghi nhận.</p>
        </div>
        <Link to="/staff/queue" className="rounded-xl bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-emerald-800">Mở hàng đợi điều phối</Link>
      </header>

      <section aria-label="Bộ lọc thống kê" className="flex flex-wrap items-end gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <label className="grid gap-1 text-sm font-medium text-slate-700">Từ ngày<input className="rounded-lg border border-slate-300 px-3 py-2" type="date" value={from} onChange={(event) => change('from', event.target.value)} /></label>
        <label className="grid gap-1 text-sm font-medium text-slate-700">Đến ngày<input className="rounded-lg border border-slate-300 px-3 py-2" type="date" value={through} onChange={(event) => change('through', event.target.value)} /></label>
        <label className="grid gap-1 text-sm font-medium text-slate-700">Cơ sở<select disabled={optionsLoading} className="min-w-48 rounded-lg border border-slate-300 px-3 py-2 disabled:bg-slate-100" value={facility} onChange={(event) => change('facility', event.target.value)}><option value="">Tất cả cơ sở</option>{facilities.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        <label className="grid gap-1 text-sm font-medium text-slate-700">Bác sĩ<select disabled={optionsLoading} className="min-w-48 rounded-lg border border-slate-300 px-3 py-2 disabled:bg-slate-100" value={doctor} onChange={(event) => change('doctor', event.target.value)}><option value="">Tất cả bác sĩ</option>{doctorsForFacility.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        {optionsLoading && <span role="status" className="pb-2 text-sm text-slate-500">Đang tải lựa chọn…</span>}
        {optionsError && <div role="alert" className="flex items-center gap-3 pb-2 text-sm text-rose-700"><span>{optionsError}</span><button type="button" className="font-semibold underline" onClick={() => retryOptions()}>Thử tải lại</button></div>}
      </section>

      {invalidRange && <p role="alert" className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">Khoảng ngày không hợp lệ.</p>}
      {error && <div role="alert" className="flex items-center justify-between gap-3 rounded-lg bg-rose-50 p-3 text-sm text-rose-800"><span>{error}</span><button className="font-semibold underline" onClick={() => retrySummary()}>Thử lại</button></div>}
      {loading && !error && <DataLoadingState className="min-h-64 flex flex-col items-center justify-center text-slate-400" label="Đang tải thống kê…" />}
      {!invalidRange && !loading && !error && summary && <>
        <p className="text-sm text-slate-500">Khoảng thời gian: {new Date(summary.range.from).toLocaleDateString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' })} – {new Date(new Date(summary.range.to).getTime() - 1).toLocaleDateString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' })} (giờ Việt Nam)</p>
        <section aria-label="Chỉ số vận hành" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {cards.map(({ key, title, href, icon: Icon, tone }) => (
            <Link key={key} to={href} className="group rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-emerald-300 hover:shadow-md">
              <div className="flex items-start justify-between gap-3">
                <span className="text-sm font-semibold text-slate-600">{title}</span>
                <span className={`rounded-xl p-2.5 ${iconTone[tone]}`}><Icon aria-hidden="true" size={20} /></span>
              </div>
              <strong className="mt-4 block text-3xl font-bold tracking-tight text-slate-900">{number(summary.metrics[key])}</strong>
              <span className="mt-3 block text-xs font-semibold text-emerald-700 group-hover:underline">Xem chi tiết →</span>
            </Link>
          ))}
        </section>
        <ChatbotOutcomes metrics={summary.metrics} />
        <p className="text-xs text-slate-500">“AI hoàn tất không cần can thiệp” là chỉ số quy trình dựa trên sự kiện đã ghi nhận, không đánh giá độ chính xác lâm sàng.</p>
      </>}
    </main>
  )
}

function ChatbotOutcomes({ metrics }: { metrics: Metrics }) {
  const rows = [
    { label: 'AI hoàn tất, không cần nhân viên can thiệp', value: metrics.chat_cases_ai_handled_without_escalation, color: 'bg-sky-600' },
    { label: 'Chatbot chuyển nhân viên', value: metrics.chat_escalations, color: 'bg-amber-500' },
  ]
  const max = Math.max(...rows.map((row) => row.value), 1)
  const total = rows.reduce((sum, row) => sum + row.value, 0)
  return (
    <section aria-label="Kết quả xử lý ca chatbot" className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div><h2 className="text-lg font-bold text-slate-900">Kết quả xử lý ca chatbot</h2><p className="mt-1 text-sm text-slate-500">So sánh các ca AI tự hoàn tất và ca cần chuyển nhân viên trong kỳ.</p></div>
        <span className="rounded-full bg-slate-100 px-3 py-1 text-sm font-semibold text-slate-700">{number(total)} ca</span>
      </div>
      <div role="img" aria-label={`Biểu đồ ca chatbot: AI tự hoàn tất ${number(rows[0].value)} ca; chuyển nhân viên ${number(rows[1].value)} ca.`} className="mt-6 space-y-5">
        {rows.map((row) => (
          <div key={row.label}>
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-sm"><span className="font-medium text-slate-700">{row.label}</span><strong className="text-slate-900">{number(row.value)}</strong></div>
            <div className="h-3 overflow-hidden rounded-full bg-slate-100"><div className={`h-full rounded-full ${row.color} transition-[width] duration-500`} style={{ width: `${(row.value / max) * 100}%` }} /></div>
          </div>
        ))}
      </div>
      {total === 0 && <p className="mt-4 text-sm text-slate-500">Chưa có ca chatbot trong khoảng thời gian đã chọn.</p>}
    </section>
  )
}
