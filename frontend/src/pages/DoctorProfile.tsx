import { useEffect, useState } from 'react'
import { ArrowLeft, CalendarDays, GraduationCap, Languages, MapPin, Stethoscope, UserRound } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { TypewriterLoader } from '../components/TypewriterLoader'
import { fetchDoctorDetail } from '../features/appointment-booking/api'
import type { Doctor } from '../features/appointment-booking/api'
import './DoctorProfile.css'

const languageNames: Record<string, string> = {
  vi: 'Tiếng Việt', en: 'Tiếng Anh', fr: 'Tiếng Pháp', de: 'Tiếng Đức',
  ja: 'Tiếng Nhật', ko: 'Tiếng Hàn', zh: 'Tiếng Trung', ru: 'Tiếng Nga', es: 'Tiếng Tây Ban Nha',
}

function Portrait({ doctor }: { doctor: Doctor }) {
  const [failed, setFailed] = useState(false)
  return <div className="doctor-profile__portrait">
    {doctor.avatar_url && !failed
      ? <img src={doctor.avatar_url} alt={`Ảnh ${doctor.full_name}`} width={176} height={220}
          decoding="async" referrerPolicy="no-referrer" onError={() => setFailed(true)} />
      : <div className="doctor-profile__portrait-empty"><UserRound size={48} strokeWidth={1.25} aria-hidden="true" /><span>Chưa có ảnh bác sĩ</span></div>}
  </div>
}

function Section({ title, values }: { title: string; values?: string[] }) {
  if (!values?.length) return null
  return <section className="doctor-profile__panel"><h2>{title}</h2>
    <ul className="doctor-profile__list">{values.map((value, i) => <li key={`${value}-${i}`}>{value}</li>)}</ul>
  </section>
}

export default function DoctorProfile() {
  const { id } = useParams()
  const [doctor, setDoctor] = useState<Doctor | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    let active = true
    setDoctor(null)
    setError('')
    if (!id) { setError('Không tìm thấy hồ sơ bác sĩ.'); return }
    void fetchDoctorDetail(id).then(value => { if (active) setDoctor(value) })
      .catch(() => { if (active) setError('Không thể tải hồ sơ bác sĩ. Vui lòng thử lại sau.') })
    return () => { active = false }
  }, [id])

  const bookingParams = new URLSearchParams(doctor ? { doctorId: doctor.id } : {})
  const primaryFacility = doctor?.facilities?.find(item => item.is_primary) || doctor?.facilities?.[0]
  if (primaryFacility) bookingParams.set('facilityId', primaryFacility.facility_id)
  if (doctor?.specialties?.[0]) bookingParams.set('specialtyId', doctor.specialties[0].specialty_id)
  const credentials = doctor ? [...(doctor.honors || []), ...(doctor.academic_ranks || []), ...(doctor.degrees || [])].join(' · ') || doctor.title : ''
  const canBook = doctor && (doctor.professional_role || 'Bác sĩ') === 'Bác sĩ' && doctor.booking_enabled

  return <main className="doctor-profile">
    <nav aria-label="Điều hướng hồ sơ bác sĩ">
      <Link to="/patient/doctors" className="doctor-profile__back"><ArrowLeft size={18} aria-hidden="true" />Danh sách bác sĩ</Link>
    </nav>
    {error ? <p role="alert" className="doctor-profile__error">{error}</p>
      : !doctor ? <div role="status" className="flex items-center gap-3 p-5 text-app-secondary"><TypewriterLoader size="md" />Đang tải hồ sơ bác sĩ…</div>
      : <>
        <header className="doctor-profile__hero">
          <Portrait key={`${doctor.id}:${doctor.avatar_url}`} doctor={doctor} />
          <div className="doctor-profile__identity">
            <p className="doctor-profile__eyebrow">Hồ sơ chuyên gia y tế</p>
            {credentials && <p className="doctor-profile__credentials">{credentials}</p>}
            <h1>{doctor.full_name}</h1>
            <p className="doctor-profile__role"><Stethoscope size={17} aria-hidden="true" />{doctor.professional_role || 'Bác sĩ'}</p>
            <div className="doctor-profile__specialties">{doctor.specialties?.map(item => <span key={item.specialty_id}>{item.name}</span>)}</div>
            {doctor.position && <p className="doctor-profile__muted">{doctor.position}</p>}
            {primaryFacility?.facility?.name && <p className="doctor-profile__location"><MapPin size={16} aria-hidden="true" />{primaryFacility.facility.name}</p>}
            {canBook ? <Link to={`/patient/appointments?${bookingParams}`} className="doctor-profile__booking"><CalendarDays size={18} aria-hidden="true" />Yêu cầu lịch khám</Link>
              : <p className="doctor-profile__muted">Hiện chưa tiếp nhận yêu cầu lịch khám trực tuyến.</p>}
          </div>
        </header>

        <div className="doctor-profile__columns">
          <div className="doctor-profile__content">
            <section className="doctor-profile__panel"><h2>Giới thiệu</h2>
              <p className="doctor-profile__bio">{doctor.bio || 'Thông tin giới thiệu đang được cập nhật.'}</p>
            </section>
            <Section title="Quá trình đào tạo" values={doctor.education} />
            <Section title="Kinh nghiệm làm việc" values={doctor.work_history} />
            <Section title="Thành tựu" values={doctor.awards} />
            {!!doctor.services?.length && <Section title="Dịch vụ chuyên môn" values={doctor.services.map(item => item.name)} />}
          </div>
          <aside className="doctor-profile__sidebar" aria-label="Thông tin chuyên môn và nơi làm việc">
            <section className="doctor-profile__panel"><h2>Thông tin chuyên môn</h2>
              <dl className="doctor-profile__facts">
                {credentials && <div><dt><GraduationCap size={16} aria-hidden="true" />Học vị & danh hiệu</dt><dd>{credentials}</dd></div>}
                {doctor.experience_years != null && <div><dt>Kinh nghiệm</dt><dd>{doctor.experience_years} năm</dd></div>}
                <div><dt><Languages size={16} aria-hidden="true" />Ngôn ngữ</dt><dd>{doctor.languages?.length ? doctor.languages.map(language => languageNames[language.toLowerCase()] || language).join(', ') : 'Đang cập nhật'}</dd></div>
              </dl>
            </section>
            <section className="doctor-profile__panel"><h2>Nơi làm việc</h2>
              {doctor.facilities?.length ? <div className="doctor-profile__facilities">{doctor.facilities.map(item => <div key={item.facility_id}>
                <MapPin size={17} aria-hidden="true" /><div><h3>{item.facility?.name || 'Cơ sở đang cập nhật'}</h3>
                  {item.department && <p>{item.department}</p>}{item.position && <p>{item.position}</p>}{item.room && <p>Phòng: {item.room}</p>}
                </div>
              </div>)}</div> : <p className="doctor-profile__muted">Thông tin nơi làm việc đang được cập nhật.</p>}
            </section>
          </aside>
        </div>
      </>}
  </main>
}
