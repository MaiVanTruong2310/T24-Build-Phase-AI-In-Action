import { Visible } from '../features/uiVisibility/Visible'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { MapPin, MessageCircleHeart, Search, SlidersHorizontal, UserRound, X } from 'lucide-react'
import { peekQuery, rememberQuery } from '../app/queryCache'
import { fetchDoctorFacets, fetchDoctors, fetchFacilities, fetchSpecialties } from '../features/appointment-booking/api'
import type { Doctor, Facility, Specialty } from '../features/appointment-booking/api'
import './DoctorDirectory.css'

// Giữ bộ lọc + kết quả gần nhất để quay lại tab thấy ngay danh sách cũ, API vẫn làm mới ngầm.
const VIEW_KEY = 'doctors:view'
const VIEW_TTL_MS = 30 * 60_000
type Facets = { honors: string[]; academic_ranks: string[]; degrees: string[]; languages: string[]; professional_roles: string[] }
type SavedView = { name: string; specialtyId: string; facilityId: string; honor: string; rank: string; degree: string; language: string; professionalRole: string; page: number; doctors: Doctor[] }
const EMPTY_FACETS: Facets = { honors: [], academic_ranks: [], degrees: [], languages: [], professional_roles: [] }

const QUICK_SPECIALTIES = 10

function initials(name: string) {
  const words = name.trim().split(/\s+/).filter(Boolean)
  return (words.length > 1 ? words[words.length - 2][0] + words[words.length - 1][0] : words[0]?.slice(0, 2) || '').toUpperCase()
}

function DoctorAvatar({ doctor }: { doctor: Doctor }) {
  const [failed, setFailed] = useState(false)
  return <span className="dd-avatar" aria-hidden={!doctor.avatar_url || failed ? true : undefined}>
    {doctor.avatar_url && !failed
      ? <img src={doctor.avatar_url} alt={`Ảnh ${doctor.full_name}`} width={72} height={72} loading="lazy" decoding="async" referrerPolicy="no-referrer" onError={() => setFailed(true)} />
      : <span className="dd-avatar__fallback">{initials(doctor.full_name) || <UserRound size={28} strokeWidth={1.6} />}</span>}
  </span>
}

function bookingHref(doctor: Doctor) {
  const params = new URLSearchParams({ doctorId: doctor.id })
  const facility = doctor.facilities?.find(item => item.is_primary) || doctor.facilities?.[0]
  if (facility) params.set('facilityId', facility.facility_id)
  if (doctor.specialties?.[0]) params.set('specialtyId', doctor.specialties[0].specialty_id)
  return `/patient/appointments?${params}`
}

export default function DoctorDirectory() {
  const [saved] = useState(() => peekQuery<SavedView>(VIEW_KEY))
  const [doctors, setDoctors] = useState<Doctor[]>(() => saved?.doctors ?? [])
  const [facets, setFacets] = useState<Facets>(() => peekQuery<Facets>('catalog:doctor-facets', true) ?? EMPTY_FACETS)
  const [allSpecialties, setAllSpecialties] = useState<Specialty[]>(() => peekQuery<Specialty[]>('catalog:specialties:limit=150', true) ?? [])
  const [allFacilities, setAllFacilities] = useState<Facility[]>(() => peekQuery<Facility[]>('catalog:facilities:limit=50', true) ?? [])
  const [specialties, setSpecialties] = useState<Specialty[]>(allSpecialties)
  const [facilities, setFacilities] = useState<Facility[]>(allFacilities)
  const [name, setName] = useState(saved?.name ?? '')
  const [specialtyId, setSpecialtyId] = useState(saved?.specialtyId ?? '')
  const [facilityId, setFacilityId] = useState(saved?.facilityId ?? '')
  const [honor, setHonor] = useState(saved?.honor ?? '')
  const [rank, setRank] = useState(saved?.rank ?? '')
  const [degree, setDegree] = useState(saved?.degree ?? '')
  const [language, setLanguage] = useState(saved?.language ?? '')
  const [professionalRole, setProfessionalRole] = useState(saved?.professionalRole ?? '')
  const [page, setPage] = useState(saved?.page ?? 0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Chỉ về trang 1 khi bộ lọc thực sự đổi (không reset trang đã lưu lúc mới mở tab).
  const filterKey = [name, specialtyId, facilityId, honor, rank, degree, language, professionalRole].join('|')
  const lastFilterKey = useRef(filterKey)
  const firstSearch = useRef(true)
  useEffect(() => {
    if (lastFilterKey.current === filterKey) return
    lastFilterKey.current = filterKey
    setPage(0)
  }, [filterKey])

  useEffect(() => {
    rememberQuery<SavedView>(VIEW_KEY, { name, specialtyId, facilityId, honor, rank, degree, language, professionalRole, page, doctors }, VIEW_TTL_MS)
  }, [name, specialtyId, facilityId, honor, rank, degree, language, professionalRole, page, doctors])
  useEffect(() => {
    let active = true
    void Promise.all([fetchDoctorFacets(), fetchSpecialties(), fetchFacilities()]).then(([options, s, f]) => {
      if (!active) return
      setFacets(options); setAllSpecialties(s); setAllFacilities(f); setSpecialties(s); setFacilities(f)
    }).catch(() => { if (active) setError('Không thể tải danh mục bác sĩ.') })
    return () => { active = false }
  }, [])

  useEffect(() => {
    let active = true
    if (facilityId) {
      void fetchSpecialties({ facilityId }).then(s => {
        if (!active) return
        setSpecialties(s)
        setSpecialtyId(prev => s.some(x => x.id === prev) ? prev : '')
      }).catch(() => undefined)
    } else {
      setSpecialties(allSpecialties)
    }
    return () => { active = false }
  }, [facilityId, allSpecialties])

  useEffect(() => {
    let active = true
    if (specialtyId && !facilityId) {
      void fetchFacilities({ specialtyId }).then(f => { if (active) setFacilities(f) }).catch(() => undefined)
    } else if (!specialtyId && allFacilities.length > 0) {
      setFacilities(allFacilities)
    }
    return () => { active = false }
  }, [specialtyId, facilityId, allFacilities])
  useEffect(() => {
    let active = true
    // Lần tải đầu không cần debounce gõ phím.
    const delay = firstSearch.current ? 0 : 250
    firstSearch.current = false
    const timeout = window.setTimeout(() => {
      setLoading(true)
      void fetchDoctors({ name: name.trim(), specialtyId, facilityId, honor, academicRank: rank,
        degree, language, professionalRole, offset: page * 20, limit: 20 }).then(value => {
        if (active) { setDoctors(value); setError('') }
      }).catch(() => { if (active) setError('Không thể tìm bác sĩ.') })
        .finally(() => { if (active) setLoading(false) })
    }, delay)
    return () => { active = false; window.clearTimeout(timeout) }
  }, [name, specialtyId, facilityId, honor, rank, degree, language, professionalRole, page])

  const [advancedOpen, setAdvancedOpen] = useState(false)
  const resetFilters = () => { setName(''); setSpecialtyId(''); setFacilityId(''); setHonor(''); setRank(''); setDegree(''); setLanguage(''); setProfessionalRole(''); setSpecialties(allSpecialties); setFacilities(allFacilities) }
  const advancedCount = [honor, rank, degree, language, professionalRole].filter(Boolean).length
  const activeChips: Array<{ key: string; label: string; clear: () => void }> = [
    name.trim() && { key: 'name', label: `Tên: ${name.trim()}`, clear: () => setName('') },
    facilityId && { key: 'facility', label: facilities.find(x => x.id === facilityId)?.name || allFacilities.find(x => x.id === facilityId)?.name || 'Cơ sở', clear: () => setFacilityId('') },
    specialtyId && { key: 'specialty', label: specialties.find(x => x.id === specialtyId)?.name || allSpecialties.find(x => x.id === specialtyId)?.name || 'Chuyên khoa', clear: () => setSpecialtyId('') },
    honor && { key: 'honor', label: honor, clear: () => setHonor('') },
    rank && { key: 'rank', label: rank, clear: () => setRank('') },
    degree && { key: 'degree', label: degree, clear: () => setDegree('') },
    language && { key: 'language', label: language, clear: () => setLanguage('') },
    professionalRole && { key: 'role', label: professionalRole, clear: () => setProfessionalRole('') },
  ].filter(Boolean) as Array<{ key: string; label: string; clear: () => void }>
  const quickSpecialties = (() => {
    const head = specialties.slice(0, QUICK_SPECIALTIES)
    const picked = specialties.find(x => x.id === specialtyId)
    return picked && !head.some(x => x.id === picked.id) ? [picked, ...head.slice(0, QUICK_SPECIALTIES - 1)] : head
  })()

  return <main className="dd">
    <Visible id="doctors.heading"><header className="dd-head">
      <p className="dd-kicker">Chuyên gia y tế</p>
      <h1 className="dd-title">Tìm bác sĩ phù hợp</h1>
      <p className="dd-sub">Lọc theo chuyên khoa, cơ sở và trình độ chuyên môn trước khi gửi yêu cầu khám.</p>
    </header></Visible>

    <Visible id="doctors.search"><section className="dd-bar" role="search" aria-label="Tìm bác sĩ">
      <label className="dd-search">
        <Search className="dd-search__icon" size={20} aria-hidden="true" />
        <span className="sr-only">Tên bác sĩ</span>
        <input value={name} onChange={e => setName(e.target.value)} placeholder="Tìm theo tên bác sĩ" autoComplete="off" />
        {name && <button type="button" className="dd-search__clear" onClick={() => setName('')} aria-label="Xóa tên đang tìm"><X size={16} aria-hidden="true" /></button>}
      </label>
      <label className="dd-field"><span className="dd-field__label">Cơ sở</span>
        <select value={facilityId} onChange={e => setFacilityId(e.target.value)}><option value="">Tất cả cơ sở</option>{facilities.map(x => <option key={x.id} value={x.id}>{x.name}</option>)}</select></label>
      <label className="dd-field"><span className="dd-field__label">Chuyên khoa</span>
        <select value={specialtyId} onChange={e => setSpecialtyId(e.target.value)}><option value="">Tất cả chuyên khoa</option>{specialties.map(x => <option key={x.id} value={x.id}>{x.name}</option>)}</select></label>
      <Visible id="doctors.advanced" inline><button type="button" className={`dd-adv-btn${advancedCount ? ' is-on' : ''}`} aria-expanded={advancedOpen} aria-controls="dd-adv" onClick={() => setAdvancedOpen(v => !v)}>
        <SlidersHorizontal size={18} aria-hidden="true" /><span>Bộ lọc nâng cao</span>{advancedCount > 0 && <b className="dd-adv-btn__count">{advancedCount}</b>}
      </button></Visible>
    </section></Visible>

    <Visible id="doctors.chips">{quickSpecialties.length > 0 && <div className="dd-chips" role="group" aria-label="Chọn nhanh chuyên khoa">
      <button type="button" className="dd-chip" aria-pressed={!specialtyId} onClick={() => setSpecialtyId('')}>Tất cả</button>
      {quickSpecialties.map(x => <button key={x.id} type="button" className="dd-chip" aria-pressed={specialtyId === x.id} onClick={() => setSpecialtyId(specialtyId === x.id ? '' : x.id)}>{x.name}</button>)}
    </div>}</Visible>

    {advancedOpen && <div className="dd-backdrop" onClick={() => setAdvancedOpen(false)} aria-hidden="true" />}
    {advancedOpen && <section id="dd-adv" className="dd-adv" aria-label="Bộ lọc nâng cao">
      <div className="dd-adv__head"><p>Bộ lọc nâng cao</p><button type="button" className="dd-adv__done" onClick={() => setAdvancedOpen(false)}>Xong</button></div>
      <div className="dd-adv__grid">
        <label className="dd-field"><span className="dd-field__label">Danh hiệu</span><select value={honor} onChange={e => setHonor(e.target.value)}><option value="">Tất cả danh hiệu</option>{facets.honors.map(x => <option key={x}>{x}</option>)}</select></label>
        <label className="dd-field"><span className="dd-field__label">Học hàm</span><select value={rank} onChange={e => setRank(e.target.value)}><option value="">Tất cả học hàm</option>{facets.academic_ranks.map(x => <option key={x}>{x}</option>)}</select></label>
        <label className="dd-field"><span className="dd-field__label">Học vị / chuyên khoa</span><select value={degree} onChange={e => setDegree(e.target.value)}><option value="">Tất cả học vị</option>{facets.degrees.map(x => <option key={x}>{x}</option>)}</select></label>
        <label className="dd-field"><span className="dd-field__label">Ngôn ngữ</span><select value={language} onChange={e => setLanguage(e.target.value)}><option value="">Tất cả ngôn ngữ</option>{facets.languages.map(x => <option key={x}>{x}</option>)}</select></label>
        <label className="dd-field"><span className="dd-field__label">Nghề nghiệp</span><select value={professionalRole} onChange={e => setProfessionalRole(e.target.value)}><option value="">Tất cả</option>{facets.professional_roles.map(x => <option key={x}>{x}</option>)}</select></label>
      </div>
    </section>}

    {error && <p role="alert" className="dd-error">{error}</p>}

    <div className="dd-status" aria-live="polite">
      <p className="dd-count">{loading ? 'Đang tìm…' : `Trang ${page + 1} · ${doctors.length} bác sĩ`}</p>
      {activeChips.length > 0 && <div className="dd-active">
        {activeChips.map(chip => <button key={chip.key} type="button" className="dd-active__chip" onClick={chip.clear} aria-label={`Bỏ lọc ${chip.label}`}><span>{chip.label}</span><X size={14} aria-hidden="true" /></button>)}
        <button type="button" className="dd-active__reset" onClick={resetFilters}>Xóa bộ lọc</button>
      </div>}
    </div>

    {loading && doctors.length === 0 && <div className="dd-grid" aria-hidden="true">{Array.from({ length: 6 }, (_, i) => <div key={i} className="dd-card dd-card--skeleton"><span className="dd-skel dd-skel--avatar" /><span className="dd-skel dd-skel--line" /><span className="dd-skel dd-skel--line dd-skel--short" /><span className="dd-skel dd-skel--btn" /></div>)}</div>}

    <div className="dd-grid">{doctors.map(doctor => {
      const credentials = [...(doctor.honors || []), ...(doctor.academic_ranks || []), ...(doctor.degrees || [])].join(' · ') || doctor.title || ''
      const doctorSpecialties = doctor.specialties || []
      const facility = doctor.facilities?.find(item => item.is_primary) || doctor.facilities?.[0]
      const otherFacilities = (doctor.facilities?.length || 0) - 1
      const canBook = (doctor.professional_role || 'Bác sĩ') === 'Bác sĩ' && doctor.booking_enabled
      return <article key={doctor.id} className="dd-card">
        <div className="dd-card__top">
          <DoctorAvatar doctor={doctor} />
          <div className="dd-card__id">
            <h2 className="dd-card__name">{doctor.full_name}</h2>
            <p className="dd-card__role">{doctor.professional_role || 'Bác sĩ'}</p>
            {credentials && <p className="dd-card__cred">{credentials}</p>}
          </div>
        </div>
        <div className="dd-tags">
          {doctorSpecialties.length === 0 && <span className="dd-tag dd-tag--muted">Chuyên khoa đang cập nhật</span>}
          {doctorSpecialties.slice(0, 2).map(x => <span key={x.specialty_id} className="dd-tag">{x.name}</span>)}
          {doctorSpecialties.length > 2 && <span className="dd-tag dd-tag--more">+{doctorSpecialties.length - 2}</span>}
        </div>
        {facility && <p className="dd-card__place"><MapPin size={16} aria-hidden="true" /><span>{facility.facility?.name || 'Cơ sở'}{facility.department ? ` · ${facility.department}` : ''}{otherFacilities > 0 ? ` (+${otherFacilities} cơ sở)` : ''}</span></p>}
        {doctor.experience_years != null && <p className="dd-card__meta">{doctor.experience_years} năm kinh nghiệm</p>}
        <div className="dd-card__actions">
          <Link to={`/patient/doctors/${doctor.id}`} className="dd-btn dd-btn--ghost">Xem hồ sơ</Link>
          {canBook && <Link to={bookingHref(doctor)} className="dd-btn dd-btn--primary">Đặt lịch</Link>}
        </div>
      </article>
    })}</div>

    {!loading && doctors.length === 0 && !error && <div className="dd-empty">
      <p className="dd-empty__title">Chưa tìm thấy bác sĩ phù hợp</p>
      <p className="dd-empty__text">Thử bỏ bớt bộ lọc, hoặc mô tả triệu chứng để trợ lý gợi ý chuyên khoa.</p>
      <div className="dd-empty__actions">
        {activeChips.length > 0 && <button type="button" className="dd-btn dd-btn--ghost" onClick={resetFilters}>Xóa bộ lọc</button>}
        <Link to="/patient" className="dd-btn dd-btn--primary"><MessageCircleHeart size={18} aria-hidden="true" />Hỏi trợ lý VCare+</Link>
      </div>
    </div>}

    <div className="dd-pager"><button disabled={page === 0 || loading} onClick={() => setPage(x => x - 1)} className="dd-btn dd-btn--ghost">Trước</button><span>Trang {page + 1}</span><button disabled={doctors.length < 20 || loading} onClick={() => setPage(x => x + 1)} className="dd-btn dd-btn--ghost">Sau</button></div>
  </main>
}
