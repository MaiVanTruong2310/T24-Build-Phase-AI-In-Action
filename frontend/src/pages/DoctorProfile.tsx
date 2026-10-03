import { TypewriterLoader } from '../components/TypewriterLoader';
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchDoctorDetail } from '../features/appointment-booking/api'
import type { Doctor } from '../features/appointment-booking/api'

const Section = ({ title, values }: { title: string; values?: string[] }) => values?.length ? <section className="rounded-2xl border bg-white light:bg-app-surface p-5 shadow-sm"><h2 className="text-lg font-bold">{title}</h2><ul className="mt-3 list-disc space-y-2 pl-5 text-sm leading-6 text-slate-700 light:text-app-text">{values.map((value, i) => <li key={`${value}-${i}`}>{value}</li>)}</ul></section> : null

export default function DoctorProfile() {
  const { id } = useParams()
  const [doctor, setDoctor] = useState<Doctor | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    if (!id) return
    void fetchDoctorDetail(id).then(setDoctor).catch(() => setError('Không thể tải hồ sơ bác sĩ.'))
  }, [id])
  if (error) return <p role="alert" className="rounded-xl bg-red-50 p-5 text-red-700">{error}</p>
  if (!doctor) return <div role="status" className="flex items-center gap-3 p-5 text-slate-500 light:text-app-secondary"><TypewriterLoader size="md" />Đang tải hồ sơ bác sĩ…</div>
  const bookingParams = new URLSearchParams({ doctorId: doctor.id })
  if (doctor.facilities?.[0]) bookingParams.set('facilityId', doctor.facilities[0].facility_id)
  if (doctor.specialties?.[0]) bookingParams.set('specialtyId', doctor.specialties[0].specialty_id)
  return <main className="mx-auto max-w-5xl space-y-5 pb-12">
    <Link to="/patient/doctors" className="text-sm font-semibold text-blue-700 light:text-app-primary">← Danh sách bác sĩ</Link>
    <header className="rounded-3xl bg-gradient-to-r from-blue-950 light:from-app-primary-strong to-blue-700 light:to-app-primary-strong p-6 text-white md:p-8">
      <p className="text-sm text-blue-200 light:text-app-on-primary">{[...(doctor.honors || []), ...(doctor.academic_ranks || []), ...(doctor.degrees || [])].join(' · ') || doctor.title || 'Bác sĩ'}</p>
      <h1 className="mt-2 text-3xl font-bold">{doctor.full_name}</h1>
      <p className="mt-1 text-xs font-semibold uppercase text-blue-200 light:text-app-on-primary">{doctor.professional_role || 'Bác sĩ'}</p>
      <p className="mt-2 text-sm text-blue-100 light:text-app-on-primary">{doctor.specialties?.map(x => x.name).join(' · ')}</p>
      {doctor.experience_years != null && <p className="mt-2 text-sm text-blue-100 light:text-app-on-primary">{doctor.experience_years} năm kinh nghiệm</p>}
      {(doctor.professional_role || 'Bác sĩ') === 'Bác sĩ' && doctor.booking_enabled && <Link to={`/patient/appointments?${bookingParams}`} className="mt-5 inline-block rounded-lg bg-white light:bg-app-surface px-5 py-3 text-sm font-bold text-blue-900 light:text-app-primary-strong">Yêu cầu lịch khám</Link>}
    </header>
    {doctor.bio && <section className="rounded-2xl border bg-white light:bg-app-surface p-5 shadow-sm"><h2 className="text-lg font-bold">Giới thiệu</h2><p className="mt-3 whitespace-pre-line text-sm leading-6 text-slate-700 light:text-app-text">{doctor.bio}</p></section>}
    <section className="rounded-2xl border bg-white light:bg-app-surface p-5 shadow-sm"><h2 className="text-lg font-bold">Nơi làm việc</h2><div className="mt-3 space-y-3">{doctor.facilities?.map(item => <div key={item.facility_id} className="rounded-xl bg-slate-50 light:bg-app-page p-3 text-sm"><strong>{item.facility?.name || 'Cơ sở'}</strong>{item.department && <p>{item.department}</p>}{item.position && <p className="text-slate-600 light:text-app-secondary">{item.position}</p>}</div>)}</div></section>
    {doctor.languages?.length ? <p className="rounded-2xl border bg-white light:bg-app-surface p-5 text-sm shadow-sm"><strong>Ngôn ngữ:</strong> {doctor.languages.join(', ')}</p> : null}
    <Section title="Quá trình đào tạo" values={doctor.education} />
    <Section title="Kinh nghiệm làm việc" values={doctor.work_history} />
    <Section title="Thành tựu" values={doctor.awards} />
  </main>
}
