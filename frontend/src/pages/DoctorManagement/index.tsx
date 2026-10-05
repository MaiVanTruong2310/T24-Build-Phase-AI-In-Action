import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchFacilities } from '../../features/appointment-booking/api'
import type { Facility } from '../../features/appointment-booking/api'
import { fetchSpecialties, fetchStaffDoctors } from './api'
import type { Specialty, StaffDoctor } from './api'
import * as E from 'fp-ts/Either'

export default function DoctorManagement() {
  const [doctors, setDoctors] = useState<StaffDoctor[]>([])
  const [specialties, setSpecialties] = useState<Specialty[]>([])
  const [facilities, setFacilities] = useState<Facility[]>([])
  const [name, setName] = useState('')
  const [specialtyId, setSpecialtyId] = useState('')
  const [facilityId, setFacilityId] = useState('')
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    setPage(0)
  }, [name, specialtyId, facilityId])
  useEffect(() => {
    void Promise.all([fetchSpecialties()(), fetchFacilities()]).then(([s, f]) => {
      if (E.isRight(s)) setSpecialties(s.right)
      setFacilities(f)
    }).catch(() => setError('Không thể tải danh mục.'))
  }, [])
  useEffect(() => {
    let active = true
    const timeout = window.setTimeout(() => {
      setLoading(true)
      void fetchStaffDoctors({ name: name.trim(), specialtyId, facilityId, offset: page * 20, limit: 20 }).then(values => {
        if (active) { setDoctors(values); setError('') }
      }).catch(cause => { if (active) setError(cause instanceof Error ? cause.message : 'Không thể tải bác sĩ.') })
        .finally(() => { if (active) setLoading(false) })
    }, 250)
    return () => { active = false; window.clearTimeout(timeout) }
  }, [name, specialtyId, facilityId, page])

  return <main className="min-h-screen bg-slate-50 p-4 md:p-8">
    <div className="mx-auto max-w-6xl space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3"><div><h1 className="text-2xl font-bold">Quản lý bác sĩ</h1><p className="mt-1 text-sm text-slate-600">Tìm theo tên, chuyên khoa và cơ sở công tác.</p></div><Link to="/staff/doctors/create" className="rounded-lg bg-sky-700 px-4 py-2 font-semibold text-white">+ Thêm bác sĩ</Link></header>
      <section className="grid gap-3 rounded-xl border bg-white p-4 shadow-sm sm:grid-cols-3">
        <label className="text-sm">Tên bác sĩ<input value={name} onChange={e => setName(e.target.value)} placeholder="Nhập tên" className="mt-1 w-full rounded-lg border p-2" /></label>
        <label className="text-sm">Chuyên khoa<select value={specialtyId} onChange={e => setSpecialtyId(e.target.value)} className="mt-1 w-full rounded-lg border p-2"><option value="">Tất cả</option>{specialties.map(x => <option key={x.id} value={x.id}>{x.name}</option>)}</select></label>
        <label className="text-sm">Cơ sở<select value={facilityId} onChange={e => setFacilityId(e.target.value)} className="mt-1 w-full rounded-lg border p-2"><option value="">Tất cả</option>{facilities.map(x => <option key={x.id} value={x.id}>{x.name}</option>)}</select></label>
      </section>
      {error && <p role="alert" className="rounded-xl bg-red-50 p-4 text-sm text-red-700">{error}</p>}
      <p className="text-sm text-slate-500">{loading ? 'Đang tải…' : `Đang hiển thị ${doctors.length} bác sĩ`}</p>
      <div className="grid gap-4 md:grid-cols-2">{doctors.map(doc => <article key={doc.id} className="rounded-xl border bg-white p-5 shadow-sm">
        <div className="flex items-start justify-between gap-3"><div><h2 className="text-lg font-bold">{doc.full_name}</h2><p className="text-xs text-slate-500">{doc.code} · {doc.professional_role}</p></div><span className={`rounded-full px-3 py-1 text-xs font-semibold ${doc.booking_enabled ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>{doc.booking_enabled ? 'Nhận lịch' : 'Tạm ngưng đặt lịch'}</span></div>
        <p className="mt-3 text-sm text-sky-800">{[...doc.honors, ...doc.academic_ranks, ...doc.degrees].join(' · ') || doc.title || 'Chưa cập nhật danh xưng'}</p>
        <p className="mt-2 text-sm">{doc.specialties.map(x => x.specialty?.name).filter(Boolean).join(', ') || 'Chưa gán chuyên khoa'}</p>
        <div className="mt-3 space-y-1 text-sm text-slate-600">{doc.facilities.length ? doc.facilities.map(item => <p key={item.facility_id}>📍 {item.facility?.name || 'Cơ sở'}{item.department ? ` · ${item.department}` : ''}</p>) : <p>Chưa gán cơ sở</p>}</div>
        {doc.experience_years != null && <p className="mt-3 text-xs text-slate-500">{doc.experience_years} năm kinh nghiệm</p>}
        <div className="mt-4 flex gap-4"><Link to={`/patient/doctors/${doc.id}`} className="text-sm font-semibold text-sky-700">Xem hồ sơ →</Link><Link to={`/staff/doctors/${doc.id}/edit`} className="text-sm font-semibold text-slate-700">Chỉnh sửa →</Link></div>
      </article>)}</div>
      {!loading && doctors.length === 0 && !error && <p className="rounded-xl border bg-white p-8 text-center text-slate-500">Không tìm thấy bác sĩ phù hợp.</p>}
      <div className="flex justify-end gap-2"><button disabled={page === 0 || loading} onClick={() => setPage(x => x - 1)} className="rounded-lg border px-4 py-2 text-sm disabled:opacity-40">Trước</button><span className="px-2 py-2 text-sm">Trang {page + 1}</span><button disabled={doctors.length < 20 || loading} onClick={() => setPage(x => x + 1)} className="rounded-lg border px-4 py-2 text-sm disabled:opacity-40">Sau</button></div>
    </div>
  </main>
}
