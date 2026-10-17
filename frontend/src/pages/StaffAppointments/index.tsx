import { useCallback, useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { Activity, CalendarCheck, Clock3, FileText, Mail, MapPin, Phone, RefreshCw, Search, Stethoscope, UserRound, X } from 'lucide-react'
import { useDispatch, useSelector } from 'react-redux'
import { cancelStaffAppointment, fetchPendingBookings, fetchStaffBooking, type PendingBooking } from '../AppointmentApproval/api'
import { DataLoadingState } from '../../components/DataLoadingState'
import type { AppDispatch, RootState } from '../../app/store'
import { applyAppointmentFilters, clearAppointmentFilters, clearAppointmentViews, loadAppointmentsFailed, loadAppointmentsStarted, loadAppointmentsSucceeded, setAppointmentOffset, setDateDraft, setSearchDraft, staffAppointmentsKey } from '../../features/staff-appointments/staffAppointmentsSlice'

const PAGE_SIZE = 20
const appointmentTime = (value: string) => new Date(value).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true, timeZone: 'Asia/Ho_Chi_Minh' })
const appointmentDate = (value: string) => new Date(value).toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric', timeZone: 'Asia/Ho_Chi_Minh' })
const appointmentRange = (booking: Pick<PendingBooking, 'starts_at' | 'ends_at'>) => `${appointmentTime(booking.starts_at)} – ${appointmentTime(booking.ends_at)} · ${appointmentDate(booking.starts_at)}`

export default function StaffAppointments() {
  const dispatch = useDispatch<AppDispatch>()
  const appointments = useSelector((state: RootState) => state.staffAppointments)
  const { query, date, appliedQuery, appliedDate, offset } = appointments
  const pageKey = staffAppointmentsKey(appliedQuery, appliedDate, offset)
  const page = appointments.views[pageKey]
  const items = page?.items ?? []
  const total = page?.total ?? 0
  const loading = Boolean(appointments.loadingKeys[pageKey])
  const error = appointments.errorKey === pageKey ? appointments.error : ''
  const [target, setTarget] = useState<PendingBooking | null>(null)
  const [reason, setReason] = useState('')
  const [cancelError, setCancelError] = useState('')
  const [saving, setSaving] = useState(false)
  const [success, setSuccess] = useState('')
  const [detail, setDetail] = useState<PendingBooking | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState('')
  const cancelDialog = useRef<HTMLDialogElement>(null)
  const detailDialog = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    if (target && !cancelDialog.current?.open) cancelDialog.current?.showModal()
    else if (!target && cancelDialog.current?.open) cancelDialog.current.close()
  }, [target])

  useEffect(() => {
    if (detail && !detailDialog.current?.open) detailDialog.current?.showModal()
    else if (!detail && detailDialog.current?.open) detailDialog.current.close()
  }, [detail])

  const load = useCallback(async () => {
    const key = staffAppointmentsKey(appliedQuery, appliedDate, offset)
    const generation = appointments.generation
    dispatch(loadAppointmentsStarted({ key, generation }))
    try {
      const page = await fetchPendingBookings({ status: 'confirmed', scheduledOnly: true, q: appliedQuery || undefined, date: appliedDate || undefined, offset, limit: PAGE_SIZE })
      dispatch(loadAppointmentsSucceeded({ key, generation, items: page.items, total: page.total }))
      if (offset > 0 && offset >= page.total) dispatch(setAppointmentOffset(Math.max(0, Math.floor((page.total - 1) / PAGE_SIZE) * PAGE_SIZE)))
    } catch (cause) {
      dispatch(loadAppointmentsFailed({ key, generation, error: cause instanceof Error ? cause.message : 'KhÃ´ng táº£i Ä‘Æ°á»£c danh sÃ¡ch lá»‹ch Ä‘Ã£ xÃ¡c nháº­n.' }))
    }
  }, [appliedDate, appliedQuery, appointments.generation, dispatch, offset])

  useEffect(() => { if (!page && !loading && !error) void load() }, [appointments.filtersVersion, error, load, loading, page])

  const openCancel = (booking: PendingBooking) => {
    setTarget(booking)
    setReason('')
    setCancelError('')
  }

  const openDetail = async (booking: PendingBooking) => {
    setDetail(booking)
    setDetailLoading(true)
    setDetailError('')
    try {
      setDetail(await fetchStaffBooking(booking.id))
    } catch (cause) {
      setDetailError(cause instanceof Error ? cause.message : 'KhÃ´ng táº£i Ä‘Æ°á»£c chi tiáº¿t booking.')
    } finally {
      setDetailLoading(false)
    }
  }

  const cancel = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!target || !reason.trim() || saving) return
    setSaving(true)
    setCancelError('')
    try {
      await cancelStaffAppointment(target.id, reason)
      dispatch(clearAppointmentViews())
      setTarget(null)
      setReason('')
      setSuccess(`ÄÃ£ há»§y lá»‹ch khÃ¡m ${target.booking_code}.`)
    } catch (cause) {
      setCancelError(cause instanceof Error ? cause.message : 'KhÃ´ng thá»ƒ há»§y lá»‹ch khÃ¡m. Vui lÃ²ng thá»­ láº¡i.')
    } finally {
      setSaving(false)
    }
  }

  const hasFilters = Boolean(appliedQuery || appliedDate)
  const clearFilters = () => dispatch(clearAppointmentFilters())

  return <section className="mx-auto max-w-7xl space-y-5 p-4 sm:p-6 lg:p-8">
    <header className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <p className="text-sm font-semibold text-teal-800">Điều phối khám</p>
        <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">Lịch khám đã xác nhận</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">Theo dõi giờ hẹn, thông tin liên hệ và nơi khám của các booking đã được duyệt.</p>
      </div>
      <button type="button" onClick={() => void load()} disabled={loading} className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition-colors hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700 disabled:cursor-not-allowed disabled:opacity-50">
        <RefreshCw size={16} aria-hidden="true" className={loading ? 'animate-spin' : ''} />Làm mới
      </button>
    </header>

    {success && <div role="status" className="flex items-center justify-between gap-3 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900"><span>{success}</span><button type="button" onClick={() => setSuccess('')} aria-label="Đóng thông báo" className="grid min-h-11 min-w-11 place-items-center rounded-lg hover:bg-emerald-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800"><X size={18} aria-hidden="true" /></button></div>}

    <form onSubmit={event => { event.preventDefault(); dispatch(applyAppointmentFilters()) }} className="grid gap-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5 lg:grid-cols-[minmax(0,1fr)_240px_auto] lg:items-end">
      <label htmlFor="appointments-search" className="block text-sm font-semibold text-slate-800">Tìm bệnh nhân hoặc mã lịch
        <span className="relative mt-1.5 block"><Search size={17} aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" /><input id="appointments-search" value={query} onChange={event => dispatch(setSearchDraft(event.target.value))} placeholder="Tên bệnh nhân hoặc mã booking" className="min-h-11 w-full rounded-xl border border-slate-300 bg-white py-2 pl-10 pr-3 text-base font-normal text-slate-900 outline-none transition focus:border-teal-700 focus:ring-2 focus:ring-teal-100" /></span>
      </label>
      <label htmlFor="appointments-date" className="block text-sm font-semibold text-slate-800">Ngày khám
        <input id="appointments-date" type="date" value={date} onChange={event => dispatch(setDateDraft(event.target.value))} className="mt-1.5 block min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-base font-normal text-slate-900 outline-none transition focus:border-teal-700 focus:ring-2 focus:ring-teal-100" />
      </label>
      <div className="flex flex-wrap gap-2 lg:justify-end">
        <button type="submit" className="inline-flex min-h-11 flex-1 items-center justify-center gap-2 rounded-xl bg-teal-800 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-teal-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700 sm:flex-none"><Search size={16} aria-hidden="true" />Tìm kiếm</button>
        {hasFilters && <button type="button" onClick={clearFilters} className="min-h-11 rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 transition-colors hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700">Xóa bộ lọc</button>}
      </div>
    </form>

    {error ? <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 sm:p-5"><p role="alert" className="text-sm leading-6 text-rose-900">{error}</p><button type="button" onClick={() => void load()} className="mt-3 min-h-11 rounded-xl border border-rose-300 bg-white px-4 py-2 text-sm font-semibold text-rose-900 transition-colors hover:bg-rose-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rose-700">Thử tải lại</button></div> : <section aria-labelledby="appointments-list-title" className="overflow-hidden rounded-2xl border border-slate-200 bg-slate-50/70 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 bg-white px-4 py-4 sm:px-5">
        <div><h2 id="appointments-list-title" className="font-bold text-slate-900">Danh sách lịch khám</h2><p className="mt-0.5 text-sm text-slate-600">Giờ hẹn và thông tin người khám</p></div>
        <p aria-live="polite" className="text-sm font-medium text-slate-600">{loading ? 'Đang tải…' : `${total.toLocaleString('vi-VN')} lịch khám`}</p>
      </div>
      {loading ? <DataLoadingState className="flex flex-col items-center justify-center py-12 text-slate-500" label="Đang tải lịch khám…" /> : items.length === 0 ? <div className="px-5 py-12 text-center sm:py-16">
        <CalendarCheck className="mx-auto mb-3 text-teal-800" size={36} aria-hidden="true" />
        <p className="font-semibold text-slate-900">{hasFilters ? 'Không tìm thấy lịch phù hợp' : 'Chưa có lịch khám đã xác nhận'}</p>
        <p className="mx-auto mt-1 max-w-md text-sm leading-6 text-slate-600">{hasFilters ? 'Thử đổi từ khóa hoặc ngày khám để tìm lịch cần xem.' : 'Lịch khám đã xác nhận sẽ xuất hiện tại đây.'}</p>
        {hasFilters && <button type="button" onClick={clearFilters} className="mt-4 min-h-11 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-800 transition-colors hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700">Xóa bộ lọc</button>}
      </div> : <ol aria-label="Các lịch khám đã xác nhận" className="grid grid-cols-1 gap-3 p-3 sm:gap-4 sm:p-4">
        {items.map(item => <li key={item.id} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition-shadow hover:shadow-md sm:p-5">
          <div className="flex items-start justify-between gap-3">
            <div className="flex min-w-0 items-start gap-3">
              <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-teal-50 text-teal-800"><CalendarCheck size={21} aria-hidden="true" /></span>
              <div className="min-w-0"><p className="whitespace-nowrap text-base font-bold leading-6 text-slate-950"><time dateTime={item.starts_at}>{appointmentTime(item.starts_at)}</time><span aria-hidden="true"> – </span><time dateTime={item.ends_at}>{appointmentTime(item.ends_at)}</time></p><time dateTime={item.starts_at} className="mt-0.5 block text-sm text-slate-600">{appointmentDate(item.starts_at)}</time></div>
            </div>
            <span className="shrink-0 rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-900">Đã xác nhận</span>
          </div>
          <div className="mt-4 border-t border-slate-100 pt-4">
            <div className="flex flex-wrap items-baseline justify-between gap-2"><h3 className="text-base font-bold text-slate-950">{item.patient_name}</h3><span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-700">{item.booking_code}</span></div>
            <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-600"><span className="inline-flex items-center gap-1.5"><Phone size={14} aria-hidden="true" />{item.patient_phone || 'Chưa có số điện thoại'}</span><span className="inline-flex min-w-0 items-center gap-1.5 break-all"><Mail size={14} aria-hidden="true" />{item.patient_email || 'Chưa có email'}</span></div>
          </div>
          <dl className="mt-4 grid gap-x-4 gap-y-3 border-t border-slate-100 pt-4 sm:grid-cols-2">
            <div><dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Khoa · dịch vụ</dt><dd className="mt-1 text-sm font-semibold leading-5 text-slate-900">{item.specialty_name} · {item.service_name || 'Khám riêng'}</dd><dd className="mt-0.5 text-sm text-slate-600">Bác sĩ: {item.doctor_name}</dd></div>
            <div><dt className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500"><MapPin size={13} aria-hidden="true" />Cơ sở</dt><dd className="mt-1 text-sm font-semibold leading-5 text-slate-900">{item.facility_name}</dd><dd className="mt-0.5 text-sm leading-5 text-slate-600">{item.facility_address || 'Chưa có địa chỉ'}</dd></div>
          </dl>
          <div className="mt-4 flex flex-wrap gap-2 border-t border-slate-100 pt-4">
            <button type="button" onClick={() => void openDetail(item)} className="min-h-11 flex-1 rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-800 transition-colors hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700 sm:flex-none">Chi tiết booking</button>
            <button type="button" onClick={() => openCancel(item)} className="min-h-11 flex-1 rounded-xl border border-rose-200 px-4 py-2 text-sm font-semibold text-rose-800 transition-colors hover:bg-rose-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rose-700 sm:flex-none">Hủy lịch</button>
          </div>
        </li>)}
      </ol>}
      <footer className="flex flex-wrap items-center gap-3 border-t border-slate-200 bg-white px-4 py-3 sm:px-5">
        <span className="mr-auto text-sm text-slate-600">{total ? `${offset + 1}–${Math.min(offset + PAGE_SIZE, total)} / ${total}` : '0 lịch'}</span>
        <button type="button" aria-label="Trang trước" disabled={loading || offset === 0} onClick={() => dispatch(setAppointmentOffset(Math.max(0, offset - PAGE_SIZE)))} className="min-h-11 rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-800 transition-colors hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700 disabled:cursor-not-allowed disabled:opacity-40">Trước</button>
        <button type="button" aria-label="Trang sau" disabled={loading || offset + PAGE_SIZE >= total} onClick={() => dispatch(setAppointmentOffset(offset + PAGE_SIZE))} className="min-h-11 rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-800 transition-colors hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700 disabled:cursor-not-allowed disabled:opacity-40">Sau</button>
      </footer>
    </section>}
    <dialog ref={detailDialog} onCancel={event => { event.preventDefault(); setDetail(null) }} aria-labelledby="booking-detail-title" className="m-auto flex max-h-[90dvh] w-[calc(100%-1.5rem)] max-w-3xl flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white p-0 text-slate-900 shadow-2xl backdrop:bg-slate-950/55 sm:max-h-[86dvh]">
      {detail && <>
        <header className="relative shrink-0 overflow-hidden bg-gradient-to-r from-teal-800 via-teal-700 to-cyan-700 px-5 py-5 text-white sm:px-7">
          <div className="absolute -right-10 -top-16 h-48 w-48 rounded-full bg-white/10" />
          <div className="relative flex items-start justify-between gap-4"><div className="flex items-start gap-3"><div className="rounded-2xl bg-white/15 p-3"><FileText size={22} /></div><div><div className="flex flex-wrap items-center gap-2"><h2 id="booking-detail-title" className="text-xl font-bold">Chi tiết booking</h2><span className="rounded-full bg-emerald-300/20 px-2.5 py-1 text-xs font-semibold text-emerald-50">{detail.status === 'confirmed' ? 'Đã xác nhận' : detail.status}</span></div><p className="mt-1 text-sm text-teal-50">Mã booking: {detail.booking_code}</p></div></div><button type="button" onClick={() => setDetail(null)} aria-label="Đóng chi tiết" className="rounded-xl p-2 text-white/80 transition hover:bg-white/15 hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-white"><X size={20} /></button></div>
        </header>
        <div className="schedule-scrollbar min-h-0 flex-1 space-y-4 overflow-y-auto bg-slate-50/70 p-4 sm:p-6">
          {detailLoading ? <p role="status" className="rounded-2xl bg-white py-14 text-center text-sm text-slate-500 shadow-sm">Đang tải chi tiết booking…</p> : detailError ? <div className="rounded-2xl border border-rose-200 bg-white p-5"><p role="alert" className="text-sm text-rose-700">{detailError}</p><button type="button" onClick={() => void openDetail(detail)} className="mt-3 rounded-lg border border-rose-200 px-3 py-2 text-sm font-medium text-rose-800 hover:bg-rose-50">Thử tải lại</button></div> : <>
            <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5"><div className="mb-4 flex items-center gap-2"><UserRound size={18} className="text-teal-700" /><h3 className="font-bold text-slate-800">Thông tin bệnh nhân</h3></div><div className="grid gap-4 sm:grid-cols-2"><Detail label="Họ và tên" value={detail.patient_name} /><Detail label="Điện thoại" value={detail.patient_phone} icon={<Phone size={15} />} /><Detail label="Email" value={detail.patient_email} icon={<Mail size={15} />} /></div></section>
            <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5"><div className="mb-4 flex items-center gap-2"><Stethoscope size={18} className="text-teal-700" /><h3 className="font-bold text-slate-800">Thông tin lịch khám</h3></div><div className="grid gap-4 sm:grid-cols-2"><Detail label="Khoa" value={detail.specialty_name} /><Detail label="Dịch vụ" value={detail.service_name || 'Khám riêng'} /><Detail label="Bác sĩ" value={detail.doctor_name} /><Detail label="Cơ sở" value={detail.facility_name} icon={<MapPin size={15} />} /><Detail label="Địa chỉ" value={detail.facility_address} /><Detail label="Khung giờ" value={`${appointmentRange(detail)}`} icon={<Clock3 size={15} />} /></div></section>
            <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5"><div className="mb-3 flex items-center gap-2"><FileText size={18} className="text-teal-700" /><h3 className="font-bold text-slate-800">Nội dung booking</h3></div><Detail label="Lý do khám" value={detail.reason} />{detail.patient_note && <div className="mt-4 border-t border-slate-100 pt-4"><Detail label="Ghi chú cho bác sĩ" value={detail.patient_note} /></div>}</section>
            {detail.ai_triage && <section className="rounded-2xl border border-violet-200 bg-violet-50/70 p-4 sm:p-5"><div className="mb-3 flex items-center gap-2"><Activity size={18} className="text-violet-700" /><h3 className="font-bold text-violet-950">Thông tin tiếp nhận ca</h3></div>{detail.ai_triage.symptoms && <p className="whitespace-pre-wrap text-sm leading-6 text-violet-950">{detail.ai_triage.symptoms}</p>}{detail.ai_triage.suggested_department_name && <p className="mt-3 text-sm text-violet-800">Khoa đề xuất: {detail.ai_triage.suggested_department_name}</p>}</section>}
          </>}
        </div>
        <footer className="flex shrink-0 justify-end border-t border-slate-200 bg-white px-5 py-3 sm:px-7"><button type="button" onClick={() => setDetail(null)} className="rounded-xl bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700">Đóng</button></footer>
      </>}
    </dialog>

    <dialog ref={cancelDialog} onCancel={event => { event.preventDefault(); if (!saving) setTarget(null) }} aria-labelledby="cancel-appointment-title" className="m-auto w-[calc(100%-2rem)] max-w-lg rounded-2xl bg-white p-5 shadow-2xl backdrop:bg-slate-950/40">
      {target && <><header className="flex items-start justify-between gap-3"><div><h2 id="cancel-appointment-title" className="text-lg font-bold text-slate-900">Há»§y lá»‹ch khÃ¡m?</h2><p className="mt-1 text-sm text-slate-600">{target.patient_name} Â· {appointmentRange(target)} Â· {target.booking_code}</p></div><button type="button" disabled={saving} onClick={() => setTarget(null)} aria-label="ÄÃ³ng" className="rounded-lg p-2 text-slate-500 hover:bg-slate-100"><X size={18} /></button></header><form onSubmit={event => void cancel(event)} className="mt-4 space-y-4"><label className="block text-sm font-medium text-slate-700">LÃ½ do há»§y <span aria-hidden="true">*</span><textarea required minLength={1} maxLength={500} rows={4} value={reason} onChange={event => setReason(event.target.value)} className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 font-normal" /></label>{cancelError && <p role="alert" className="text-sm text-rose-700">{cancelError}</p>}<footer className="flex justify-end gap-2"><button type="button" disabled={saving} onClick={() => setTarget(null)} className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium">Äá»ƒ sau</button><button type="submit" disabled={saving || !reason.trim()} className="rounded-lg bg-rose-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{saving ? 'Äang há»§yâ€¦' : 'XÃ¡c nháº­n há»§y lá»‹ch'}</button></footer></form></>}
    </dialog>
  </section>
}

function Detail({ label, value, icon }: { label: string; value: string | null | undefined; icon?: ReactNode }) {
  return <div><p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">{icon}{label}</p><p className="mt-1 whitespace-pre-wrap break-words text-sm font-medium leading-5 text-slate-900">{value || 'â€”'}</p></div>
}
