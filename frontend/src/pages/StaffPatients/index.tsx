import { useEffect, useState, type FormEvent } from 'react'
import { fetchStaffPatient, fetchStaffPatients, type StaffPatient, type StaffPatientDetail } from './api'

const PAGE_SIZE = 20
const statusNames: Record<string, string> = {
  active: 'Đang hoạt động',
  pending_verification: 'Chờ xác minh',
  inactive: 'Ngừng hoạt động',
}
const genderNames: Record<string, string> = { male: 'Nam', female: 'Nữ', other: 'Khác', unspecified: 'Chưa cung cấp' }
const dateTime = (value?: string | null) => value ? new Date(value).toLocaleString('vi-VN') : '—'

function PatientDetails({ patientId }: { patientId: string }) {
  const [patient, setPatient] = useState<StaffPatientDetail | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [retry, setRetry] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError('')
    void fetchStaffPatient(patientId, controller.signal).then(setPatient).catch((cause: unknown) => {
      if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Không thể tải hồ sơ bệnh nhân.')
    }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [patientId, retry])

  if (loading) return <p role="status" className="p-5 text-sm text-slate-600">Đang tải hồ sơ…</p>
  if (error) return <div className="p-5"><p role="alert" className="text-sm text-rose-700">{error}</p><button type="button" onClick={() => setRetry(value => value + 1)} className="mt-3 rounded-lg border px-3 py-2 text-sm">Thử lại</button></div>
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
  const [draft, setDraft] = useState({ q: '', status: '', gender: '', created_from: '', created_to: '' })
  const [filters, setFilters] = useState(draft)
  const [patients, setPatients] = useState<StaffPatient[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [selected, setSelected] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    const params = new URLSearchParams({ offset: String(offset), limit: String(PAGE_SIZE) })
    Object.entries(filters).forEach(([key, value]) => { if (value.trim()) params.set(key, value.trim()) })
    setLoading(true)
    setError('')
    void fetchStaffPatients(params, controller.signal).then(page => {
      setPatients(page.items)
      setTotal(page.total)
    }).catch((cause: unknown) => {
      if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Không thể tải danh sách bệnh nhân.')
    }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [filters, offset, retry])

  const search = (event: FormEvent) => {
    event.preventDefault()
    setOffset(0)
    setSelected(null)
    setFilters({ ...draft })
  }
  const reset = () => {
    const empty = { q: '', status: '', gender: '', created_from: '', created_to: '' }
    setDraft(empty)
    setFilters(empty)
    setOffset(0)
    setSelected(null)
  }
  const first = total ? offset + 1 : 0
  const last = Math.min(offset + PAGE_SIZE, total)

  return <section className="space-y-5 p-4 sm:p-6 lg:p-8">
    <header><p className="text-xs font-semibold uppercase tracking-wider text-emerald-700">Không gian điều phối</p><h1 className="mt-1 text-2xl font-bold text-slate-900">Tra cứu hồ sơ bệnh nhân</h1><p className="mt-1 text-sm text-slate-600">Tìm theo họ tên; thông tin định danh được che khi xem chi tiết.</p></header>

    <form onSubmit={search} className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-2 xl:grid-cols-6">
      <label className="sm:col-span-2 xl:col-span-2"><span className="mb-1 block text-xs font-medium text-slate-600">Họ và tên</span><input value={draft.q} onChange={event => setDraft({ ...draft, q: event.target.value })} maxLength={200} placeholder="Nhập họ tên bệnh nhân" className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-100" /></label>
      <label><span className="mb-1 block text-xs font-medium text-slate-600">Trạng thái</span><select value={draft.status} onChange={event => setDraft({ ...draft, status: event.target.value })} className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"><option value="">Tất cả</option><option value="active">Đang hoạt động</option><option value="pending_verification">Chờ xác minh</option><option value="inactive">Ngừng hoạt động</option></select></label>
      <label><span className="mb-1 block text-xs font-medium text-slate-600">Giới tính</span><select value={draft.gender} onChange={event => setDraft({ ...draft, gender: event.target.value })} className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"><option value="">Tất cả</option><option value="male">Nam</option><option value="female">Nữ</option><option value="other">Khác</option><option value="unspecified">Chưa cung cấp</option></select></label>
      <label><span className="mb-1 block text-xs font-medium text-slate-600">Tạo từ ngày</span><input type="date" value={draft.created_from} onChange={event => setDraft({ ...draft, created_from: event.target.value })} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></label>
      <label><span className="mb-1 block text-xs font-medium text-slate-600">Đến ngày</span><input type="date" value={draft.created_to} onChange={event => setDraft({ ...draft, created_to: event.target.value })} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></label>
      <div className="flex gap-2 sm:col-span-2 xl:col-span-6"><button type="submit" className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-800">Tìm kiếm</button><button type="button" onClick={reset} className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">Xóa bộ lọc</button></div>
    </form>

    {error ? <div className="rounded-xl border border-rose-200 bg-rose-50 p-4"><p role="alert" className="text-sm text-rose-800">{error}</p><button type="button" onClick={() => setRetry(value => value + 1)} className="mt-3 rounded-lg border border-rose-300 bg-white px-3 py-2 text-sm font-medium text-rose-800">Thử tải lại</button></div> : <>
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"><div className="flex items-center justify-between border-b border-slate-200 px-4 py-3"><h2 className="font-semibold text-slate-800">Danh sách bệnh nhân</h2><span className="text-sm text-slate-500">{loading ? 'Đang tải…' : `${total.toLocaleString('vi-VN')} hồ sơ`}</span></div>
        <div className="overflow-x-auto"><table className="w-full min-w-[720px] text-left text-sm"><thead className="bg-slate-50 text-xs text-slate-600"><tr><th className="px-4 py-3 font-semibold">Bệnh nhân</th><th className="px-4 py-3 font-semibold">Email / Điện thoại</th><th className="px-4 py-3 font-semibold">Giới tính</th><th className="px-4 py-3 font-semibold">Trạng thái</th><th className="px-4 py-3 font-semibold">Ngày tạo</th></tr></thead><tbody className="divide-y divide-slate-100">{patients.map(patient => <tr key={patient.id} className={selected === patient.id ? 'bg-emerald-50' : 'hover:bg-slate-50'}><td className="px-4 py-3"><button type="button" aria-expanded={selected === patient.id} onClick={() => setSelected(current => current === patient.id ? null : patient.id)} className="text-left font-semibold text-emerald-800 hover:underline">{patient.full_name || 'Chưa cập nhật tên'}</button><span className="mt-0.5 block text-xs text-slate-500">{patient.id}</span></td><td className="px-4 py-3"><span className="block">{patient.email || '—'}</span><span className="mt-0.5 block text-xs text-slate-500">{patient.phone || '—'}</span></td><td className="px-4 py-3">{patient.gender ? genderNames[patient.gender] || patient.gender : '—'}</td><td className="px-4 py-3">{statusNames[patient.status] || patient.status}</td><td className="px-4 py-3">{dateTime(patient.created_at)}</td></tr>)}</tbody></table></div>
        {!loading && patients.length === 0 && <p className="p-8 text-center text-sm text-slate-500">Không tìm thấy hồ sơ phù hợp.</p>}
        {loading && <p role="status" className="p-8 text-center text-sm text-slate-500">Đang tải danh sách…</p>}
        <footer className="flex flex-wrap items-center gap-3 border-t border-slate-200 px-4 py-3"><span className="mr-auto text-sm text-slate-500">{first}–{last} / {total.toLocaleString('vi-VN')}</span><button type="button" disabled={loading || offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))} className="rounded-lg border px-3 py-2 text-sm disabled:opacity-40">Trước</button><button type="button" disabled={loading || offset + PAGE_SIZE >= total} onClick={() => setOffset(offset + PAGE_SIZE)} className="rounded-lg border px-3 py-2 text-sm disabled:opacity-40">Sau</button></footer>
      </div>
      {selected && <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"><header className="flex items-center justify-between border-b px-5 py-3"><h2 className="font-semibold">Thông tin hồ sơ</h2><button type="button" onClick={() => setSelected(null)} aria-label="Đóng chi tiết" className="rounded px-2 py-1 text-slate-500 hover:bg-slate-100">Đóng</button></header><PatientDetails patientId={selected} /></section>}
    </>}
  </section>
}
