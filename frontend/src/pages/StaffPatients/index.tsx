import { useEffect, useRef, type FormEvent } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import type { AppDispatch, RootState } from '../../app/store'
import { applyPatientFilters, loadStaffPatientDetail, loadStaffPatients, resetPatientFilters, selectPatient, selectSelectedPatient, selectSelectedPatientError, selectSelectedPatientLoading, selectStaffPatientError, selectStaffPatientLoading, selectStaffPatientPage, setPatientDraft, setPatientOffset } from '../../features/staff-patients/staffPatientsSlice'
import type { StaffPatientDetail } from './api'
import { DataLoadingState } from '../../components/DataLoadingState'

const PAGE_SIZE = 20
const statusNames: Record<string, string> = {
  active: 'Đang hoạt động',
  pending_verification: 'Chờ xác minh',
  inactive: 'Ngừng hoạt động',
}
const genderNames: Record<string, string> = { male: 'Nam', female: 'Nữ', other: 'Khác', unspecified: 'Chưa cung cấp' }
const dateTime = (value?: string | null) => value ? new Date(value).toLocaleString('vi-VN') : '—'

function PatientDetails({ patient }: { patient?: StaffPatientDetail }) {
  if (!patient) return null

  return <dl className="grid gap-4 p-5 sm:grid-cols-2">
    <div><dt className="text-xs text-slate-500">Mã hồ sơ</dt><dd className="mt-1 break-all text-sm font-medium">{patient.id}</dd></div>
    <div><dt className="text-xs text-slate-500">Họ và tên</dt><dd className="mt-1 text-sm font-medium">{patient.full_name || 'Chưa cập nhật'}</dd></div>
    <div><dt className="text-xs text-slate-500">Email</dt><dd className="mt-1 break-all text-sm">{patient.email || 'Chưa cung cấp'}</dd></div>
    <div><dt className="text-xs text-slate-500">Số điện thoại</dt><dd className="mt-1 text-sm">{patient.phone || 'Chưa cung cấp'}</dd></div>
    <div><dt className="text-xs text-slate-500">Ngày sinh</dt><dd className="mt-1 text-sm">{patient.date_of_birth || 'Chưa cung cấp'}</dd></div>
    <div><dt className="text-xs text-slate-500">Giới tính</dt><dd className="mt-1 text-sm">{patient.gender ? genderNames[patient.gender] || patient.gender : 'Chưa cung cấp'}</dd></div>
    <div><dt className="text-xs text-slate-500">CCCD (đã che)</dt><dd className="mt-1 text-sm">{patient.citizen_id_masked || 'Chưa cung cấp'}</dd></div>
    <div><dt className="text-xs text-slate-500">BHYT (đã che)</dt><dd className="mt-1 text-sm">{patient.health_insurance_code_masked || 'Chưa cung cấp'}</dd></div>
    <div><dt className="text-xs text-slate-500">Trạng thái</dt><dd className="mt-1 text-sm">{statusNames[patient.status] || patient.status}</dd></div>
  </dl>
}

export default function StaffPatients() {
  const dispatch = useDispatch<AppDispatch>()
  const draft = useSelector((state: RootState) => state.staffPatients.draft)
  const filters = useSelector((state: RootState) => state.staffPatients.filters)
  const offset = useSelector((state: RootState) => state.staffPatients.offset)
  const selected = useSelector((state: RootState) => state.staffPatients.selected)
  const page = useSelector(selectStaffPatientPage)
  const patients = page?.items ?? []
  const total = page?.total ?? 0
  const error = useSelector(selectStaffPatientError)
  const loading = useSelector(selectStaffPatientLoading) || (!page && !error)
  const patient = useSelector(selectSelectedPatient)
  const detailLoading = useSelector(selectSelectedPatientLoading)
  const detailError = useSelector(selectSelectedPatientError)
  const profileDialog = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const request = dispatch(loadStaffPatients({ filters, offset }))
    return () => request.abort()
  }, [dispatch, filters, offset])

  useEffect(() => {
    if (!selected) return
    const request = dispatch(loadStaffPatientDetail({ id: selected }))
    return () => request.abort()
  }, [dispatch, selected])

  useEffect(() => {
    if (selected && profileDialog.current && !profileDialog.current.open) {
      profileDialog.current.showModal()
    }
  }, [selected])

  const closeProfileDialog = () => {
    if (profileDialog.current?.open) profileDialog.current.close()
    else dispatch(selectPatient(null))
  }

  const search = (event: FormEvent) => {
    event.preventDefault()
    dispatch(applyPatientFilters())
  }
  const reset = () => {
    dispatch(resetPatientFilters())
  }
  const first = total ? offset + 1 : 0
  const last = Math.min(offset + PAGE_SIZE, total)

  return <section className="space-y-5 p-4 sm:p-6 lg:p-8">
    <header><p className="text-xs font-semibold uppercase tracking-wider text-emerald-700">Không gian điều phối</p><h1 className="mt-1 text-2xl font-bold text-slate-900">Tra cứu hồ sơ bệnh nhân</h1><p className="mt-1 text-sm text-slate-600">Tìm theo họ tên; thông tin định danh được che khi xem chi tiết.</p></header>

    <form onSubmit={search} className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-2 xl:grid-cols-6">
      <label className="sm:col-span-2 xl:col-span-2"><span className="mb-1 block text-xs font-medium text-slate-600">Họ và tên</span><input value={draft.q} onChange={event => dispatch(setPatientDraft({ key: 'q', value: event.target.value }))} maxLength={200} placeholder="Nhập họ tên bệnh nhân" className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-100" /></label>
      <label><span className="mb-1 block text-xs font-medium text-slate-600">Trạng thái</span><select value={draft.status} onChange={event => dispatch(setPatientDraft({ key: 'status', value: event.target.value }))} className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"><option value="">Tất cả</option><option value="active">Đang hoạt động</option><option value="pending_verification">Chờ xác minh</option><option value="inactive">Ngừng hoạt động</option></select></label>
      <label><span className="mb-1 block text-xs font-medium text-slate-600">Giới tính</span><select value={draft.gender} onChange={event => dispatch(setPatientDraft({ key: 'gender', value: event.target.value }))} className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"><option value="">Tất cả</option><option value="male">Nam</option><option value="female">Nữ</option><option value="other">Khác</option><option value="unspecified">Chưa cung cấp</option></select></label>
      <label><span className="mb-1 block text-xs font-medium text-slate-600">Tạo từ ngày</span><input type="date" value={draft.created_from} onChange={event => dispatch(setPatientDraft({ key: 'created_from', value: event.target.value }))} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></label>
      <label><span className="mb-1 block text-xs font-medium text-slate-600">Đến ngày</span><input type="date" value={draft.created_to} onChange={event => dispatch(setPatientDraft({ key: 'created_to', value: event.target.value }))} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></label>
      <div className="flex gap-2 sm:col-span-2 xl:col-span-6"><button type="submit" className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-800">Tìm kiếm</button><button type="button" onClick={reset} className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">Xóa bộ lọc</button></div>
    </form>

    {error ? <div className="rounded-xl border border-rose-200 bg-rose-50 p-4"><p role="alert" className="text-sm text-rose-800">{error}</p><button type="button" onClick={() => void dispatch(loadStaffPatients({ filters, offset, force: true }))} className="mt-3 rounded-lg border border-rose-300 bg-white px-3 py-2 text-sm font-medium text-rose-800">Thử tải lại</button></div> : <>
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"><div className="flex items-center justify-between border-b border-slate-200 px-4 py-3"><h2 className="font-semibold text-slate-800">Danh sách bệnh nhân</h2><span className="text-sm text-slate-500">{loading ? 'Đang tải…' : `${total.toLocaleString('vi-VN')} hồ sơ`}</span></div>
        <div className="overflow-x-auto"><table className="w-full min-w-[720px] text-left text-sm"><thead className="bg-slate-50 text-xs text-slate-600"><tr><th className="px-4 py-3 font-semibold">Bệnh nhân</th><th className="px-4 py-3 font-semibold">Email / Điện thoại</th><th className="px-4 py-3 font-semibold">Giới tính</th><th className="px-4 py-3 font-semibold">Trạng thái</th><th className="px-4 py-3 font-semibold">Ngày tạo</th></tr></thead><tbody className="divide-y divide-slate-100">{patients.map(patient => <tr key={patient.id} className={selected === patient.id ? 'bg-emerald-50' : 'hover:bg-slate-50'}><td className="px-4 py-3"><button type="button" aria-haspopup="dialog" aria-controls="staff-patient-profile-dialog" aria-expanded={selected === patient.id} onClick={() => dispatch(selectPatient(patient.id))} className="cursor-pointer rounded-sm text-left font-semibold text-emerald-800 transition-colors hover:text-emerald-950 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700">{patient.full_name || 'Chưa cập nhật tên'}</button><span className="mt-0.5 block text-xs text-slate-500">{patient.id}</span></td><td className="px-4 py-3"><span className="block">{patient.email || '—'}</span><span className="mt-0.5 block text-xs text-slate-500">{patient.phone || '—'}</span></td><td className="px-4 py-3">{patient.gender ? genderNames[patient.gender] || patient.gender : '—'}</td><td className="px-4 py-3">{statusNames[patient.status] || patient.status}</td><td className="px-4 py-3">{dateTime(patient.created_at)}</td></tr>)}</tbody></table></div>
        {!loading && patients.length === 0 && <p className="p-8 text-center text-sm text-slate-500">Không tìm thấy hồ sơ phù hợp.</p>}
        {loading && <DataLoadingState className="py-8 flex flex-col items-center justify-center text-slate-400" label="Đang tải danh sách…" />}
        <footer className="flex flex-wrap items-center gap-3 border-t border-slate-200 px-4 py-3"><span className="mr-auto text-sm text-slate-500">{first}–{last} / {total.toLocaleString('vi-VN')}</span><button type="button" disabled={loading || offset === 0} onClick={() => dispatch(setPatientOffset(offset - PAGE_SIZE))} className="rounded-lg border px-3 py-2 text-sm disabled:opacity-40">Trước</button><button type="button" disabled={loading || offset + PAGE_SIZE >= total} onClick={() => dispatch(setPatientOffset(offset + PAGE_SIZE))} className="rounded-lg border px-3 py-2 text-sm disabled:opacity-40">Sau</button></footer>
      </div>
      {selected && <dialog id="staff-patient-profile-dialog" ref={profileDialog} onClose={() => dispatch(selectPatient(null))} onClick={event => { if (event.target === event.currentTarget) closeProfileDialog() }} aria-labelledby="staff-patient-profile-title" className="fixed inset-0 m-auto max-h-[min(90dvh,720px)] w-[min(720px,calc(100%-2rem))] max-w-none overflow-y-auto rounded-2xl border border-slate-200 bg-white p-0 shadow-2xl backdrop:bg-slate-950/50"><header className="sticky top-0 z-10 flex items-center justify-between border-b border-slate-200 bg-white px-5 py-4"><div><p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">Hồ sơ bệnh nhân</p><h2 id="staff-patient-profile-title" className="mt-1 font-semibold text-slate-900">{patient?.full_name || patients.find(item => item.id === selected)?.full_name || 'Thông tin hồ sơ'}</h2></div><button type="button" onClick={closeProfileDialog} aria-label="Đóng hồ sơ" className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700">Đóng</button></header>{detailError ? <div className="p-5"><p role="alert" className="text-sm text-rose-700">{detailError}</p><button type="button" onClick={() => void dispatch(loadStaffPatientDetail({ id: selected, force: true }))} className="mt-3 rounded-lg border px-3 py-2 text-sm">Thử lại</button></div> : detailLoading && !patient ? <DataLoadingState className="py-10 flex flex-col items-center justify-center text-slate-400" label="Đang tải hồ sơ…" /> : <PatientDetails patient={patient} />}</dialog>}
    </>}
  </section>
}
