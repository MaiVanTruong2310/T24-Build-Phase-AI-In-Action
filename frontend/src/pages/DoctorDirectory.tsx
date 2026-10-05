import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchDoctorFacets, fetchDoctors, fetchFacilities, fetchSpecialties } from '../features/appointment-booking/api'
import type { Doctor, Facility, Specialty } from '../features/appointment-booking/api'

export default function DoctorDirectory() {
  const [doctors, setDoctors] = useState<Doctor[]>([])
  const [facets, setFacets] = useState({ honors: [] as string[], academic_ranks: [] as string[], degrees: [] as string[], languages: [] as string[], professional_roles: [] as string[] })
  const [specialties, setSpecialties] = useState<Specialty[]>([])
  const [facilities, setFacilities] = useState<Facility[]>([])
  const [name, setName] = useState('')
  const [specialtyId, setSpecialtyId] = useState('')
  const [facilityId, setFacilityId] = useState('')
  const [honor, setHonor] = useState('')
  const [rank, setRank] = useState('')
  const [degree, setDegree] = useState('')
  const [language, setLanguage] = useState('')
  const [professionalRole, setProfessionalRole] = useState('')
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [allSpecialties, setAllSpecialties] = useState<Specialty[]>([])
  const [allFacilities, setAllFacilities] = useState<Facility[]>([])

  useEffect(() => {
    setPage(0)
  }, [name, specialtyId, facilityId, honor, rank, degree, language, professionalRole])
  useEffect(() => {
    void Promise.all([fetchDoctorFacets(), fetchSpecialties(), fetchFacilities()]).then(([options, s, f]) => {
      setFacets(options); setAllSpecialties(s); setAllFacilities(f); setSpecialties(s); setFacilities(f)
    }).catch(() => setError('Không thể tải danh mục bác sĩ.'))
  }, [])

  useEffect(() => {
    if (facilityId) {
      void fetchSpecialties({ facilityId }).then(s => {
        setSpecialties(s)
        setSpecialtyId(prev => s.some(x => x.id === prev) ? prev : '')
      }).catch(() => undefined)
    } else {
      setSpecialties(allSpecialties)
    }
  }, [facilityId, allSpecialties])

  useEffect(() => {
    if (specialtyId && !facilityId) {
      void fetchFacilities({ specialtyId }).then(f => setFacilities(f)).catch(() => undefined)
    } else if (!specialtyId && !facilityId && allFacilities.length > 0) {
      setFacilities(allFacilities)
    }
  }, [specialtyId, facilityId, allFacilities])
  useEffect(() => {
    let active = true
    const timeout = window.setTimeout(() => {
      setLoading(true)
      void fetchDoctors({ name: name.trim(), specialtyId, facilityId, honor, academicRank: rank,
        degree, language, professionalRole, offset: page * 20, limit: 20 }).then(value => {
        if (active) { setDoctors(value); setError('') }
      }).catch(() => { if (active) setError('Không thể tìm bác sĩ.') })
        .finally(() => { if (active) setLoading(false) })
    }, 250)
    return () => { active = false; window.clearTimeout(timeout) }
  }, [name, specialtyId, facilityId, honor, rank, degree, language, professionalRole, page])

  return <main className="mx-auto max-w-6xl space-y-6 pb-12">
    <header className="rounded-3xl bg-gradient-to-r from-blue-950 dark:from-slate-900 light:from-app-primary-strong to-blue-700 dark:to-slate-900 light:to-app-primary-strong p-6 text-white md:p-8"><p className="text-xs uppercase tracking-wider text-blue-200 light:text-app-on-primary">VCare+ · Chuyên gia y tế</p><h1 className="mt-2 text-2xl font-bold md:text-3xl">Tìm bác sĩ phù hợp</h1><p className="mt-2 text-sm text-blue-100 light:text-app-on-primary">Lọc theo chuyên khoa, cơ sở và trình độ chuyên môn trước khi gửi yêu cầu khám.</p></header>
    <section className="grid gap-3 rounded-2xl border border-app-border bg-white dark:bg-app-surface light:bg-app-surface p-4 shadow-sm sm:grid-cols-2 lg:grid-cols-4">
      <label className="text-sm">Tên bác sĩ<input value={name} onChange={e => setName(e.target.value)} placeholder="Tìm theo tên" className="mt-1 w-full rounded-lg border border-app-border p-2" /></label>
      <label className="text-sm">Cơ sở<select value={facilityId} onChange={e => setFacilityId(e.target.value)} className="mt-1 w-full rounded-lg border border-app-border p-2"><option value="">Tất cả cơ sở</option>{facilities.map(x => <option key={x.id} value={x.id}>{x.name}</option>)}</select></label>
      <label className="text-sm">Chuyên khoa<select value={specialtyId} onChange={e => setSpecialtyId(e.target.value)} className="mt-1 w-full rounded-lg border border-app-border p-2"><option value="">Tất cả chuyên khoa</option>{specialties.map(x => <option key={x.id} value={x.id}>{x.name}</option>)}</select></label>
      <label className="text-sm">Danh hiệu<select value={honor} onChange={e => setHonor(e.target.value)} className="mt-1 w-full rounded-lg border border-app-border p-2"><option value="">Tất cả danh hiệu</option>{facets.honors.map(x => <option key={x}>{x}</option>)}</select></label>
      <label className="text-sm">Học hàm<select value={rank} onChange={e => setRank(e.target.value)} className="mt-1 w-full rounded-lg border border-app-border p-2"><option value="">Tất cả học hàm</option>{facets.academic_ranks.map(x => <option key={x}>{x}</option>)}</select></label>
      <label className="text-sm">Học vị / chuyên khoa<select value={degree} onChange={e => setDegree(e.target.value)} className="mt-1 w-full rounded-lg border border-app-border p-2"><option value="">Tất cả học vị</option>{facets.degrees.map(x => <option key={x}>{x}</option>)}</select></label>
      <label className="text-sm">Ngôn ngữ<select value={language} onChange={e => setLanguage(e.target.value)} className="mt-1 w-full rounded-lg border border-app-border p-2"><option value="">Tất cả ngôn ngữ</option>{facets.languages.map(x => <option key={x}>{x}</option>)}</select></label>
      <label className="text-sm">Nghề nghiệp<select value={professionalRole} onChange={e => setProfessionalRole(e.target.value)} className="mt-1 w-full rounded-lg border border-app-border p-2"><option value="">Tất cả</option>{facets.professional_roles.map(x => <option key={x}>{x}</option>)}</select></label>
      <div className="flex items-end"><button type="button" onClick={() => { setName(''); setSpecialtyId(''); setFacilityId(''); setHonor(''); setRank(''); setDegree(''); setLanguage(''); setProfessionalRole(''); setSpecialties(allSpecialties); setFacilities(allFacilities) }} className="w-full rounded-lg border border-app-border bg-app-surface hover:bg-app-muted px-3 py-2 text-sm font-semibold text-slate-700 dark:text-app-text light:text-app-text">Xóa bộ lọc</button></div>
    </section>
    {error && <p role="alert" className="rounded-xl bg-red-50 dark:bg-red-950/50 p-4 text-sm text-red-700 dark:text-red-300">{error}</p>}
    <p className="text-sm text-slate-500 dark:text-app-secondary light:text-app-secondary">{loading ? 'Đang tìm…' : `Đang hiển thị ${doctors.length} bác sĩ`}</p>
    <div className="grid gap-4 md:grid-cols-2">{doctors.map(doctor => <article key={doctor.id} className="rounded-2xl border border-app-border bg-white dark:bg-app-surface light:bg-app-surface p-5 shadow-sm">
      <h2 className="text-lg font-bold">{doctor.full_name}</h2>
      <p className="mt-1 text-xs font-semibold uppercase text-slate-500 dark:text-app-secondary light:text-app-secondary">{doctor.professional_role || 'Bác sĩ'}</p>
      <p className="mt-1 text-sm text-blue-700 dark:text-blue-300 light:text-app-primary">{[...(doctor.honors || []), ...(doctor.academic_ranks || []), ...(doctor.degrees || [])].join(' · ') || doctor.title || 'Bác sĩ'}</p>
      <p className="mt-2 text-sm text-slate-600 dark:text-app-secondary light:text-app-secondary">{doctor.specialties?.map(x => x.name).join(', ') || 'Chuyên khoa đang cập nhật'}</p>
      <div className="mt-3 space-y-1 text-sm text-slate-600 dark:text-app-secondary light:text-app-secondary">{doctor.facilities?.map(item => <p key={item.facility_id}>📍 {item.facility?.name || 'Cơ sở'}{item.department ? ` · ${item.department}` : ''}</p>)}</div>
      {doctor.experience_years != null && <p className="mt-3 text-xs text-slate-500 dark:text-app-secondary light:text-app-secondary">{doctor.experience_years} năm kinh nghiệm</p>}
      <Link to={`/patient/doctors/${doctor.id}`} className="mt-4 inline-block rounded-lg bg-blue-700 dark:bg-blue-700 light:bg-app-primary-hover px-4 py-2 text-sm font-semibold text-white">Xem hồ sơ</Link>
    </article>)}</div>
    {!loading && doctors.length === 0 && !error && <p className="rounded-xl border border-app-border bg-white dark:bg-app-surface light:bg-app-surface p-8 text-center text-sm text-slate-500 dark:text-app-secondary light:text-app-secondary">Chưa tìm thấy bác sĩ phù hợp với bộ lọc.</p>}
    <div className="flex justify-end gap-2"><button disabled={page === 0 || loading} onClick={() => setPage(x => x - 1)} className="rounded-lg border border-app-border bg-app-surface hover:bg-app-muted px-4 py-2 text-sm disabled:opacity-40">Trước</button><span className="px-2 py-2 text-sm">Trang {page + 1}</span><button disabled={doctors.length < 20 || loading} onClick={() => setPage(x => x + 1)} className="rounded-lg border border-app-border bg-app-surface hover:bg-app-muted px-4 py-2 text-sm disabled:opacity-40">Sau</button></div>
  </main>
}
