import { Visible } from '../features/uiVisibility/Visible'
import { useEffect, useState, type ReactNode } from 'react'
import { ArrowLeft, Briefcase, CalendarDays, Languages, MapPin, MessageCircleHeart, Stethoscope, UserRound, Building2 } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { fetchDoctorDetail } from '../features/appointment-booking/api'
import type { Doctor } from '../features/appointment-booking/api'
import './DoctorProfile.css'

const languageNames: Record<string, string> = {
  vi: 'Tiếng Việt', en: 'Tiếng Anh', fr: 'Tiếng Pháp', de: 'Tiếng Đức',
  ja: 'Tiếng Nhật', ko: 'Tiếng Hàn', zh: 'Tiếng Trung', ru: 'Tiếng Nga', es: 'Tiếng Tây Ban Nha',
}

const BIO_COLLAPSE_LENGTH = 320

function initials(name: string) {
  const words = name.trim().split(/\s+/).filter(Boolean)
  return (words.length > 1 ? words[words.length - 2][0] + words[words.length - 1][0] : words[0]?.slice(0, 2) || '').toUpperCase()
}

function Portrait({ doctor }: { doctor: Doctor }) {
  const [failed, setFailed] = useState(false)
  return <div className="dp-portrait">
    {doctor.avatar_url && !failed
      ? <img src={doctor.avatar_url} alt={`Ảnh ${doctor.full_name}`} width={144} height={176}
          decoding="async" referrerPolicy="no-referrer" onError={() => setFailed(true)} />
      : <div className="dp-portrait__empty" role="img" aria-label="Chưa có ảnh bác sĩ">
          {initials(doctor.full_name) ? <span>{initials(doctor.full_name)}</span> : <UserRound size={44} strokeWidth={1.4} aria-hidden="true" />}
        </div>}
  </div>
}

function Timeline({ title, values }: { title: string; values?: string[] }) {
  if (!values?.length) return null
  return <section className="dp-panel"><h2 className="dp-h2">{title}</h2>
    <ol className="dp-timeline">{values.map((value, i) => <li key={`${value}-${i}`}>{value}</li>)}</ol>
  </section>
}

function ChipSection({ title, values }: { title: string; values?: string[] }) {
  if (!values?.length) return null
  return <section className="dp-panel"><h2 className="dp-h2">{title}</h2>
    <ul className="dp-chips">{values.map((value, i) => <li key={`${value}-${i}`}>{value}</li>)}</ul>
  </section>
}

export default function DoctorProfile() {
  const { id } = useParams()
  const [doctor, setDoctor] = useState<Doctor | null>(null)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [bioOpen, setBioOpen] = useState(false)
  const [pickedFacilityId, setPickedFacilityId] = useState('')
  useEffect(() => {
    let active = true
    setDoctor(null)
    setError('')
    setBioOpen(false)
    setPickedFacilityId('')
    if (!id) { setError('Không tìm thấy hồ sơ bác sĩ.'); return }
    void fetchDoctorDetail(id).then(value => { if (active) setDoctor(value) })
      .catch(() => { if (active) setError('Không thể tải hồ sơ bác sĩ. Vui lòng thử lại sau.') })
    return () => { active = false }
  }, [id, attempt])

  const facilities = doctor?.facilities || []
  const primaryFacility = facilities.find(item => item.is_primary) || facilities[0]
  const selectedFacility = facilities.find(item => item.facility_id === pickedFacilityId) || primaryFacility
  const bookingParams = new URLSearchParams(doctor ? { doctorId: doctor.id } : {})
  if (selectedFacility) bookingParams.set('facilityId', selectedFacility.facility_id)
  if (doctor?.specialties?.[0]) bookingParams.set('specialtyId', doctor.specialties[0].specialty_id)
  const credentials = doctor ? [...(doctor.honors || []), ...(doctor.academic_ranks || []), ...(doctor.degrees || [])].join(' · ') || doctor.title : ''
  const canBook = doctor && (doctor.professional_role || 'Bác sĩ') === 'Bác sĩ' && doctor.booking_enabled
  const languagesLabel = doctor?.languages?.length ? doctor.languages.map(language => languageNames[language.toLowerCase()] || language).join(', ') : ''
  const bioLong = (doctor?.bio?.length || 0) > BIO_COLLAPSE_LENGTH
  const quick = (doctor ? [
    doctor.experience_years != null && { key: 'exp', icon: <Briefcase size={18} aria-hidden="true" />, label: 'Kinh nghiệm', value: `${doctor.experience_years} năm` },
    languagesLabel && { key: 'lang', icon: <Languages size={18} aria-hidden="true" />, label: 'Ngôn ngữ', value: languagesLabel },
    facilities.length > 0 && { key: 'fac', icon: <Building2 size={18} aria-hidden="true" />, label: 'Nơi làm việc', value: `${facilities.length} cơ sở` },
  ] : []).filter(Boolean) as Array<{ key: string; icon: ReactNode; label: string; value: string }>

  return <main className="dp">
    <nav aria-label="Điều hướng hồ sơ bác sĩ">
      <Link to="/patient/doctors" className="dp-back"><ArrowLeft size={18} aria-hidden="true" />Danh sách bác sĩ</Link>
    </nav>

    {error ? <div role="alert" className="dp-error">
        <p>{error}</p>
        <div className="dp-error__actions">
          <button type="button" className="dp-btn dp-btn--primary" onClick={() => setAttempt(value => value + 1)}>Thử lại</button>
          <Link to="/patient/doctors" className="dp-btn dp-btn--ghost">Về danh sách</Link>
        </div>
      </div>
      : !doctor ? <div role="status" aria-label="Đang tải hồ sơ bác sĩ" className="dp-loading">
          <div className="dp-hero dp-hero--skeleton" aria-hidden="true">
            <span className="dp-skel dp-skel--portrait" />
            <div className="dp-skel-stack"><span className="dp-skel dp-skel--line" /><span className="dp-skel dp-skel--title" /><span className="dp-skel dp-skel--line dp-skel--short" /></div>
          </div>
          <span className="sr-only">Đang tải hồ sơ bác sĩ…</span>
        </div>
      : <>
        <header className="dp-hero">
          <Portrait key={`${doctor.id}:${doctor.avatar_url}`} doctor={doctor} />
          <div className="dp-identity">
            <p className="dp-kicker">Hồ sơ chuyên gia y tế</p>
            {credentials && <p className="dp-credentials">{credentials}</p>}
            <h1 className="dp-name">{doctor.full_name}</h1>
            <p className="dp-role"><Stethoscope size={17} aria-hidden="true" />{doctor.professional_role || 'Bác sĩ'}</p>
            {!!doctor.specialties?.length && <ul className="dp-specialties">{doctor.specialties.map(item => <li key={item.specialty_id}>{item.name}</li>)}</ul>}
            {doctor.position && <p className="dp-muted">{doctor.position}</p>}
            {primaryFacility?.facility?.name && <p className="dp-place"><MapPin size={16} aria-hidden="true" /><span>{primaryFacility.facility.name}</span></p>}
          </div>
        </header>

        <Visible id="doctor_profile.quick">{quick.length > 0 && <ul className="dp-quick" aria-label="Thông tin nhanh">
          {quick.map(item => <li key={item.key} className="dp-quick__item"><span className="dp-quick__icon">{item.icon}</span><span><span className="dp-quick__label">{item.label}</span><strong className="dp-quick__value">{item.value}</strong></span></li>)}
        </ul>}</Visible>

        <div className="dp-cols">
          <aside className="dp-side" aria-label="Đặt lịch và nơi làm việc">
            <Visible id="doctor_profile.booking"><section className="dp-book dp-panel">
              {canBook ? <>
                <h2 className="dp-h2">Đặt lịch khám</h2>
                <p className="dp-book__text">Gửi yêu cầu lịch khám với bác sĩ này. Điều phối viên sẽ xem lại và xác nhận lịch cho bạn.</p>
                {selectedFacility?.facility?.name && <p className="dp-book__where"><MapPin size={15} aria-hidden="true" />{selectedFacility.facility.name}</p>}
                <Link to={`/patient/appointments?${bookingParams}`} className="dp-btn dp-btn--primary dp-btn--block"><CalendarDays size={18} aria-hidden="true" />Yêu cầu lịch khám</Link>
              </> : <>
                <h2 className="dp-h2">Lịch khám</h2>
                <p className="dp-book__text">Hiện chưa tiếp nhận yêu cầu lịch khám trực tuyến cho hồ sơ này.</p>
                <Link to="/patient" className="dp-btn dp-btn--ghost dp-btn--block"><MessageCircleHeart size={18} aria-hidden="true" />Hỏi trợ lý VCare+</Link>
              </>}
            </section></Visible>

            <Visible id="doctor_profile.facilities"><section className="dp-fac dp-panel"><h2 className="dp-h2">Nơi làm việc</h2>
              {facilities.length ? <ul className="dp-fac__list">{facilities.map(item => {
                const isSelected = item.facility_id === selectedFacility?.facility_id
                const body = <>
                  <MapPin size={17} aria-hidden="true" />
                  <span className="dp-fac__text">
                    <span className="dp-fac__name">{item.facility?.name || 'Cơ sở đang cập nhật'}{item.is_primary && <em className="dp-fac__tag">Cơ sở chính</em>}</span>
                    {item.department && <span className="dp-fac__line">{item.department}</span>}
                    {item.position && <span className="dp-fac__line">{item.position}</span>}
                    {item.room && <span className="dp-fac__line">Phòng: {item.room}</span>}
                  </span>
                </>
                return <li key={item.facility_id}>
                  {canBook && facilities.length > 1
                    ? <button type="button" className={`dp-fac__item dp-fac__item--pick${isSelected ? ' is-selected' : ''}`} aria-pressed={isSelected} onClick={() => setPickedFacilityId(item.facility_id)}>{body}</button>
                    : <div className="dp-fac__item">{body}</div>}
                </li>
              })}</ul> : <p className="dp-muted">Thông tin nơi làm việc đang được cập nhật.</p>}
              {canBook && facilities.length > 1 && <p className="dp-fac__hint">Chọn cơ sở bạn muốn đặt lịch.</p>}
            </section></Visible>
          </aside>

          <div className="dp-content">
            <Visible id="doctor_profile.about"><section className="dp-panel"><h2 className="dp-h2">Giới thiệu</h2>
              <p className={`dp-bio${bioLong && !bioOpen ? ' is-clamped' : ''}`}>{doctor.bio || 'Thông tin giới thiệu đang được cập nhật.'}</p>
              {bioLong && <button type="button" className="dp-more" aria-expanded={bioOpen} onClick={() => setBioOpen(value => !value)}>{bioOpen ? 'Thu gọn' : 'Xem thêm'}</button>}
            </section></Visible>
            <Visible id="doctor_profile.details"><Timeline title="Quá trình đào tạo" values={doctor.education} />
            <Timeline title="Kinh nghiệm làm việc" values={doctor.work_history} />
            <ChipSection title="Thành tựu" values={doctor.awards} />
            {!!doctor.services?.length && <ChipSection title="Dịch vụ chuyên môn" values={doctor.services.map(item => item.name)} />}</Visible>
          </div>
        </div>
      </>}
  </main>
}
