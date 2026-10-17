import { useEffect, useMemo, useRef, useState } from 'react'
import { fetchWithAuth } from '../../app/apiClient'
import { fetchAvailability, fetchDoctorSchedules, fetchDoctors, fetchServices, fetchFacilities, fetchSpecialties, type Doctor, type Facility, type MedicalService, type Schedule, type Specialty } from '../appointment-booking/api'
import { api, dateTime, type CaseDetail, type Catalog } from './api'
import './BookingModal.css'

type Props = { case_: CaseDetail; approvedBy: string; initialDepartment?: string; initialReason?: string; onClose: () => void; onCreated: (value: CaseDetail) => void }
const localDate = (value?: string) => value || new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Ho_Chi_Minh' }).format(new Date())
const dayRange = (date: string) => ({ from: new Date(`${date}T00:00:00+07:00`).toISOString(), to: new Date(`${date}T23:59:59.999+07:00`).toISOString() })
const overlaps = (start: number, end: number, row: Schedule) => row.status !== 'cancelled' && start < new Date(row.ends_at).getTime() && end > new Date(row.starts_at).getTime()
const timeMinutes = (value: string) => Number(value.slice(0, 2)) * 60 + Number(value.slice(3))
const timeAfter = (value: string, minutes: number) => { const total = timeMinutes(value) + minutes; return `${String(Math.floor(total / 60) % 24).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}` }
const clinicTime = (value: Date) => new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Ho_Chi_Minh', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).format(value)
const freeWindows = (date: string, schedules: Schedule[]) => [[8, 12], [13, 18]].flatMap(([fromHour, toHour]) => {
  const start = new Date(`${date}T${String(fromHour).padStart(2, '0')}:00:00+07:00`).getTime()
  const end = new Date(`${date}T${String(toHour).padStart(2, '0')}:00:00+07:00`).getTime()
  let cursor = start
  const windows: string[] = []
  const busy = schedules.filter(row => row.status !== 'cancelled').map(row => [new Date(row.starts_at).getTime(), new Date(row.ends_at).getTime()] as const).filter(([rowStart, rowEnd]) => rowStart < end && rowEnd > start).sort((a, b) => a[0] - b[0])
  for (const [rowStart, rowEnd] of busy) {
    if (rowStart > cursor) windows.push(`${clinicTime(new Date(cursor))}–${clinicTime(new Date(Math.min(rowStart, end)))}`)
    cursor = Math.max(cursor, rowEnd)
    if (cursor >= end) break
  }
  if (cursor < end) windows.push(`${clinicTime(new Date(cursor))}–${clinicTime(new Date(end))}`)
  return windows
})
const searchKey = (value: string) => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('vi').replace(/đ/g, 'd').replace(/[^a-z0-9]+/g, ' ').trim()
const expandFacilityName = (value: string) => value
  .replace(/\s*\([^)]*\)/g, ' ')
  .replace(/(^|[^a-z0-9])(?:đkqt|dkqt)(?=$|[^a-z0-9])/gi, '$1Đa Khoa Quốc Tế')

export function BookingModal({ case_, approvedBy, initialDepartment, initialReason, onClose, onCreated }: Props) {
  const dialog = useRef<HTMLDialogElement>(null)
  const [catalog, setCatalog] = useState<Catalog | null>(null)
  const [facilityOptions, setFacilityOptions] = useState<Facility[]>([])
  const [specialtyOptions, setSpecialtyOptions] = useState<Specialty[]>([])
  const [doctors, setDoctors] = useState<Doctor[]>([])
  const [services, setServices] = useState<MedicalService[]>([])
  const [available, setAvailable] = useState<Schedule[]>([])
  const [daySchedules, setDaySchedules] = useState<Schedule[]>([])
  const [catalogBusy, setCatalogBusy] = useState(true)
  const [doctorBusy, setDoctorBusy] = useState(false)
  const [scheduleBusy, setScheduleBusy] = useState(false)
  const [scheduleLoaded, setScheduleLoaded] = useState(false)
  const [visitMode, setVisitMode] = useState<'private' | 'service'>(case_.plan.service_id ? 'service' : 'private')
  const [doctor, setDoctor] = useState(String(case_.plan.doctor_id || ''))
  const [specialty, setSpecialty] = useState(String(case_.plan.specialty_id || ''))
  const [service, setService] = useState(String(case_.plan.service_id || ''))
  const [facility, setFacility] = useState(String(case_.plan.facility_id || case_.facility_id || ''))
  const [date, setDate] = useState(localDate(String(case_.plan.preferred_date || case_.patient.preferred_date || '')))
  const [schedule, setSchedule] = useState(String(case_.plan.schedule_id || ''))
  const preferredPeriod = String(case_.plan.preferred_period || case_.patient.preferred_period || '')
  const [gapTime, setGapTime] = useState(preferredPeriod === 'afternoon' ? '13:00' : '08:00')
  const [gapEndTime, setGapEndTime] = useState(preferredPeriod === 'afternoon' ? '13:30' : '08:30')
  const [gapEndEdited, setGapEndEdited] = useState(false)
  const [patientName, setPatientName] = useState(case_.patient.name || '')
  const [patientPhone, setPatientPhone] = useState(case_.patient.phone || '')
  const [patientEmail, setPatientEmail] = useState(case_.patient.email || '')
  const [birthDate, setBirthDate] = useState(case_.patient.date_of_birth || '')
  const [gender, setGender] = useState(case_.patient.gender || '')
  const [reason, setReason] = useState(initialReason || case_.patient.notes || String(case_.plan.reason || ''))
  const [patientNote, setPatientNote] = useState(String(case_.patient.notes || ''))
  const [encounterType, setEncounterType] = useState<'in_person' | 'telehealth'>('in_person')
  const [agreed, setAgreed] = useState(false)
  const [busy, setBusy] = useState(false)
  const [retry, setRetry] = useState(0)
  const [error, setError] = useState('')
  const guest = !case_.patient_id
  const consultationCase = case_.source === 'consultation'
  const gapMode = !consultationCase
  const routingCandidate = case_.ai_snapshot.routing_candidate
  const routingDepartment = routingCandidate && typeof routingCandidate === 'object' && 'name' in routingCandidate
    ? String((routingCandidate as { name?: unknown }).name || '')
    : ''
  const scopedDoctorIds = useMemo(() => new Set(catalog?.doctors.map(x => x.id) || []), [catalog])
  const activeDoctors = doctors.filter(x => scopedDoctorIds.has(x.id) && (!specialty || x.specialties?.some(s => s.specialty_id === specialty)))
  const selectedDoctor = doctors.find(x => x.id === doctor)
  const selectedSchedule = available.find(x => x.id === schedule)
  const selectedService = services.find(x => x.id === service)
  const gapStart = gapTime && date ? new Date(`${date}T${gapTime}:00+07:00`) : null
  const gapMinutes = gapTime && gapEndTime ? timeMinutes(gapEndTime) - timeMinutes(gapTime) : 0
  const gapInPast = Boolean(gapStart && (gapStart.getTime() <= Date.now() || gapStart.getTime() < new Date(`${localDate()}T00:00:00+07:00`).getTime()))
  const invalidGapRange = Boolean(gapTime && gapEndTime && (gapMinutes < 5 || gapMinutes > 480))
  const outsideClinicHours = Boolean(gapTime && gapEndTime && !([[480, 720], [780, 1080]] as const).some(([from, to]) => timeMinutes(gapTime) >= from && timeMinutes(gapEndTime) <= to))
  const currentGapConflict = (() => {
    if (!gapStart) return false
    return gapInPast || invalidGapRange || daySchedules.some(row => overlaps(gapStart.getTime(), gapStart.getTime() + gapMinutes * 60000, row))
  })()
  const appointmentReady = gapMode
    ? Boolean(gapTime && gapEndTime && scheduleLoaded && !scheduleBusy && !invalidGapRange && !outsideClinicHours && !currentGapConflict)
    : Boolean(selectedSchedule && !scheduleBusy)
  const hint = (value?: string) => value ? <small className="cw-booking-selection" aria-live="polite">Đã chọn: {value}</small> : null
  const loading = (message: string) => <small className="cw-booking-field-state" role="status"><span className="cw-booking-spinner" aria-hidden="true" />{message}</small>

  useEffect(() => { const node = dialog.current; if (node && !node.open) node.showModal(); return () => { if (node?.open) node.close() } }, [])
  useEffect(() => {
    if (gapMode && !gapEndEdited) setGapEndTime(timeAfter(gapTime, selectedService?.duration_minutes || 30))
  }, [gapEndEdited, gapMode, gapTime, selectedService?.duration_minutes])
  useEffect(() => {
    let active = true
    setCatalogBusy(true)
    void api<Catalog>('/catalog').then(async value => {
      if (!active) return
      setCatalog(value)
      const facilities = await fetchFacilities()
      if (!active) return
      const facilityPreference = searchKey(expandFacilityName(String(case_.patient.facility_preference || '')))
      const scopedFacilities = facilities.filter(x => value.facilities.some(f => f.id === x.id))
      const facilityMatches = facilityPreference ? scopedFacilities.filter(x => {
        const name = searchKey(x.name)
        return name && (facilityPreference.includes(name) || name.includes(facilityPreference))
      }) : []
      setFacilityOptions(facilityMatches.length ? facilityMatches : scopedFacilities)
      const selectedFacility = facilityMatches.length === 1 ? facilityMatches[0].id : ''
      setFacility(current => value.facilities.some(x => x.id === current) ? current : selectedFacility)

      const snapshotCandidates = [case_.ai_snapshot.candidate_specialties, case_.ai_snapshot.routing_candidates]
        .flatMap(value => Array.isArray(value) ? value : [])
        .map(value => value && typeof value === 'object' && 'name' in value ? String((value as { name?: unknown }).name || '') : '')
        .filter(Boolean)
      const specialtyQueries = [...new Set([routingDepartment, initialDepartment, String(case_.ai_snapshot.suggested_department_name || ''), ...snapshotCandidates].map(x => String(x || '').trim()).filter(Boolean))]
      const searched = specialtyQueries.length
        ? (await Promise.all(specialtyQueries.map(search => fetchSpecialties({ facilityId: facility || undefined, search, limit: 50 })))).flat()
        : await fetchSpecialties({ facilityId: facility || undefined, limit: 150 })
      if (!active) return
      const uniqueSpecialties = [...new Map(searched.map(x => [x.id, x])).values()]
      const bestMatches = specialtyQueries.length ? uniqueSpecialties.filter(item => specialtyQueries.some(query => {
        const a = searchKey(item.name), b = searchKey(query)
        return a && b && (a === b || a.includes(b) || b.includes(a))
      })) : uniqueSpecialties
      const options = bestMatches.length ? bestMatches : uniqueSpecialties
      setSpecialtyOptions(options)
      const exactCandidate = specialtyQueries.map(query => {
        const key = searchKey(query)
        return uniqueSpecialties.find(item => searchKey(item.name) === key)
      }).find(Boolean)
      setSpecialty(current => options.some(x => x.id === current) ? current : exactCandidate?.id || (options.length === 1 ? options[0].id : ''))
    }).catch(e => { if (active) setError(e instanceof Error ? e.message : 'Không tải được danh mục.') }).finally(() => { if (active) setCatalogBusy(false) })
    return () => { active = false }
  }, [case_.ai_snapshot.routing_candidate, case_.ai_snapshot.routing_candidates, case_.ai_snapshot.suggested_department_name, case_.ai_snapshot.candidate_specialties, case_.patient.facility_preference, facility, initialDepartment, retry, routingDepartment])
  useEffect(() => {
    let active = true
    setDoctors([]); setServices([]); setAvailable([]); setDoctor('')
    if (!facility || !specialty || !catalog) { setDoctorBusy(false); return }
    setDoctorBusy(true)
    const servicesRequest = visitMode === 'service' ? fetchServices({ facilityId: facility, specialtyId: specialty, limit: 250 }) : Promise.resolve([])
    void servicesRequest.then(serviceRows => {
      if (!active) return
      const doctorVisitServices = serviceRows.filter(x => x.booking_mode === 'doctor_visit')
      setServices(doctorVisitServices)
      setService(current => doctorVisitServices.some(x => x.id === current) ? current : '')
    }).catch(e => { if (active) setError(e instanceof Error ? e.message : 'Không tải được bác sĩ và dịch vụ.') }).finally(() => { if (active) setDoctorBusy(false) })
    return () => { active = false }
  }, [catalog, facility, specialty, visitMode, retry])
  useEffect(() => {
    let active = true
    setDoctors([]); setDoctor(''); setAvailable([])
    if (!facility || !specialty || !catalog || (visitMode === 'service' && (!service || !services.some(x => x.id === service)))) return
    setDoctorBusy(true)
    void fetchDoctors({ facilityId: facility, specialtyId: specialty, ...(visitMode === 'service' ? { serviceId: service } : {}), bookingEnabled: true, professionalRole: 'Bác sĩ', limit: 100 }).then(rows => {
      if (active) setDoctors(rows.filter(x => scopedDoctorIds.has(x.id) && x.specialties?.some(item => item.specialty_id === specialty)))
    }).catch(e => { if (active) setError(e instanceof Error ? e.message : 'Không tải được bác sĩ theo lựa chọn.') }).finally(() => { if (active) setDoctorBusy(false) })
    return () => { active = false }
  }, [catalog, facility, specialty, visitMode, service, services, retry, scopedDoctorIds])
  useEffect(() => {
    let active = true
    setSchedule(''); setAvailable([]); setDaySchedules([]); setScheduleLoaded(false)
    if (!doctor || !facility || (visitMode === 'service' && !service) || !specialty || !date || (gapMode && (!gapTime || !gapEndTime))) { setScheduleBusy(false); return }
    const range = dayRange(date)
    setScheduleBusy(true)
    const availabilityRequest = consultationCase ? fetchAvailability(doctor, date, facility, service || undefined) : Promise.resolve([])
    void Promise.all([availabilityRequest, fetchDoctorSchedules(doctor, range.from, range.to)]).then(([slots, rows]) => {
      if (!active) return
      setAvailable(slots.filter(x => x.facility_id === facility && x.service_id === (visitMode === 'service' ? service : null) && x.capacity > 0 && x.status === 'available'))
      setDaySchedules(gapMode ? rows : [])
      setScheduleLoaded(true)
    }).catch(e => { if (active) setError(e instanceof Error ? e.message : 'Không tải được lịch bác sĩ.') }).finally(() => { if (active) setScheduleBusy(false) })
    return () => { active = false }
  }, [consultationCase, date, doctor, facility, service, specialty, visitMode, retry, gapMode, gapTime, gapEndTime])

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (busy || !appointmentReady || (!gapMode && !schedule)) return
    setBusy(true); setError('')
    try {
      const start = gapMode ? new Date(`${date}T${gapTime}:00+07:00`) : null
      const end = gapMode ? new Date(`${date}T${gapEndTime}:00+07:00`) : null
      const bookingInput = {
        case_id: case_.id, status: 'confirmed',
        version: case_.version,
        patient_id: case_.patient_id,
        approved_by_receptionist_id: approvedBy,
        ...(gapMode ? { doctor_id: doctor, facility_id: facility, starts_at: start?.toISOString(), ends_at: end?.toISOString() } : { schedule_id: schedule }),
        specialty_id: specialty, service_id: visitMode === 'service' ? service : null, encounter_type: encounterType, reason, patient_note: patientNote || null,
        patient_agreed: agreed, patient_name: guest ? patientName : null, patient_phone: guest ? patientPhone || null : null,
        patient_email: guest ? patientEmail || null : null, patient_date_of_birth: guest ? birthDate || null : null,
        patient_gender: guest ? gender || null : null,
      }
      const response = await fetchWithAuth('/bookings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(bookingInput) })
      const result = await response.json()
      if (!response.ok) throw new Error(result.message || result.detail || result.error?.message || 'Không thể tạo booking.')
      if (!result.data?.id) throw new Error('API không trả về mã booking đã tạo.')
      onCreated({ ...case_, status: 'confirmed', booking_id: result.data.id, version: case_.version + 1 })
    } catch (e) { setError(e instanceof Error ? e.message : 'Kh?ng th? t?o booking.') } finally { setBusy(false) }
  }

  return <dialog ref={dialog} className="cw-booking-dialog" aria-labelledby="cw-booking-title" onCancel={event => { event.preventDefault(); if (!busy) onClose() }}>
    <form onSubmit={submit}>
      <header><div><h2 id="cw-booking-title">Tạo booking và lịch hẹn</h2><p>Thông tin phiếu được điền sẵn; điều phối viên có thể rà soát và chỉnh sửa trước khi xác nhận.</p></div><button type="button" aria-label="Đóng" disabled={busy} onClick={onClose}>×</button></header>
      {(case_.patient.preferred_date || case_.patient.preferred_period || case_.patient.facility_preference || case_.patient.contact_time_preference) && <p className="cw-booking-intake">Mong muốn: {[case_.patient.preferred_date, case_.patient.preferred_period, case_.patient.facility_preference, case_.patient.contact_time_preference].filter(Boolean).join(' · ')}</p>}
      {error && <p className="cw-error" role="alert">{error} <button type="button" disabled={busy} onClick={() => { setError(''); setRetry(x => x + 1) }}>Thử tải lại</button></p>}
      <div className="cw-booking-grid">
        <h3 className="cw-booking-step-title">1. Chọn lịch khám</h3>
        <label>Cơ sở<select required disabled={catalogBusy} value={facility} onChange={e => { setFacility(e.target.value); setService(''); setDoctor(''); setSpecialty(''); setSchedule(''); setScheduleLoaded(false) }}><option value="">{catalogBusy ? 'Đang tải cơ sở…' : 'Chọn cơ sở'}</option>{facilityOptions.map(x => <option key={x.id} value={x.id}>{x.name}</option>)}</select>{catalogBusy && loading('Đang tải cơ sở…')}{hint(facilityOptions.find(x => x.id === facility)?.name)}</label>
        <label>Chuyên khoa<select required disabled={!facility || catalogBusy} value={specialty} onChange={e => { setSpecialty(e.target.value); setDoctor(''); setService(''); setSchedule(''); setScheduleLoaded(false) }}><option value="">{catalogBusy ? 'Đang tải chuyên khoa…' : 'Chọn chuyên khoa'}</option>{specialtyOptions.map(x => <option key={x.id} value={x.id}>{x.name}</option>)}</select>{catalogBusy && facility && loading('Đang tải chuyên khoa tại cơ sở…')}{hint(specialtyOptions.find(x => x.id === specialty)?.name)}{!catalogBusy && facility && !specialtyOptions.length && <small className="cw-booking-field-state cw-booking-field-error">Cơ sở này chưa có chuyên khoa khả dụng.</small>}</label>
        <label>Hình thức khám<select required disabled={!facility || !specialty} value={visitMode} onChange={e => { setVisitMode(e.target.value as 'private' | 'service'); setDoctor(''); setService(''); setSchedule(''); setScheduleLoaded(false) }}><option value="private">Khám riêng</option><option value="service">Khám theo dịch vụ</option></select>{hint(visitMode === 'private' ? 'Khám riêng' : 'Khám theo dịch vụ')}</label>
        {visitMode === 'service' && <label>Dịch vụ<select required disabled={!facility || !specialty || doctorBusy} value={service} onChange={e => { setService(e.target.value); setDoctor(''); setSchedule(''); setScheduleLoaded(false) }}><option value="">{doctorBusy ? 'Đang tải dịch vụ…' : 'Chọn dịch vụ'}</option>{services.map(x => <option key={x.id} value={x.id}>{x.name}</option>)}</select>{doctorBusy && loading('Đang tải dịch vụ theo cơ sở và chuyên khoa…')}{hint(selectedService?.name)}{!doctorBusy && facility && specialty && !services.length && <small className="cw-booking-field-state cw-booking-field-error">Cơ sở và chuyên khoa này chưa có dịch vụ khám bác sĩ khả dụng.</small>}</label>}
        <label>Bác sĩ<select required disabled={!facility || !specialty || (visitMode === 'service' && !service) || doctorBusy} value={doctor} onChange={e => { setDoctor(e.target.value); setSchedule(''); setScheduleLoaded(false) }}><option value="">{doctorBusy ? 'Đang tải bác sĩ…' : 'Chọn bác sĩ'}</option>{activeDoctors.map(x => <option key={x.id} value={x.id}>{x.full_name}</option>)}</select>{doctorBusy && specialty && (!visitMode || visitMode === 'private' || service) && loading('Đang tải bác sĩ theo cơ sở, chuyên khoa và hình thức khám…')}{hint(selectedDoctor?.full_name)}{!doctorBusy && facility && specialty && (visitMode === 'private' || service) && !activeDoctors.length && <small className="cw-booking-field-state cw-booking-field-error">Không có bác sĩ phù hợp với các lựa chọn này.</small>}</label>
        <label>Ngày khám<input required type="date" min={localDate()} disabled={!catalog || catalogBusy || doctorBusy || !facility || !doctor || !specialty || (visitMode === 'service' && !service)} value={date} onChange={e => { setDate(e.target.value); setSchedule(''); setScheduleBusy(true); setScheduleLoaded(false) }} />{!doctor && <small className="cw-booking-field-state">{visitMode === 'service' && !service ? 'Chọn dịch vụ trước khi chọn bác sĩ.' : 'Chọn bác sĩ để xem ngày khám.'}</small>}</label>
        {consultationCase ? <label>Giờ khám<select required disabled={!catalog || catalogBusy || doctorBusy || !facility || !doctor || !specialty || (visitMode === 'service' && !service) || !date || scheduleBusy} value={schedule} onChange={e => setSchedule(e.target.value)}><option value="">{scheduleBusy ? 'Đang kiểm tra lịch…' : 'Chọn giờ đã công bố'}</option>{available.map(x => <option key={x.id} value={x.id}>{dateTime(x.starts_at)} · còn {x.capacity} chỗ</option>)}</select>{scheduleBusy && loading('Đang tải lịch khám…')}{hint(selectedSchedule ? dateTime(selectedSchedule.starts_at) : undefined)}{!scheduleBusy && doctor && !available.length && <small className="cw-booking-field-state cw-booking-field-error">Không có lịch khám đã công bố còn chỗ.</small>}</label> : <>
          <label>Giờ bắt đầu<input required type="time" value={gapTime} onChange={e => { setGapTime(e.target.value); setGapEndEdited(false); setGapEndTime(timeAfter(e.target.value, selectedService?.duration_minutes || 30)); setScheduleBusy(true); setScheduleLoaded(false) }} disabled={!doctor || !date || scheduleBusy} />{gapInPast && <small className="cw-booking-field-state cw-booking-field-error">Vui lòng chọn thời điểm trong tương lai.</small>}{outsideClinicHours && <small className="cw-booking-field-state cw-booking-field-error">Giờ khám chỉ nhận trong buổi 08:00–12:00 hoặc 13:00–18:00.</small>}{currentGapConflict && scheduleLoaded && !scheduleBusy && <small className="cw-booking-field-state cw-booking-field-error">Khung giờ này trùng với lịch của bác sĩ.</small>}</label>
          <label>Giờ kết thúc<input required type="time" value={gapEndTime} onChange={e => { setGapEndTime(e.target.value); setGapEndEdited(true); setScheduleBusy(true); setScheduleLoaded(false) }} disabled={!doctor || !date || scheduleBusy} />{invalidGapRange && <small className="cw-booking-field-state cw-booking-field-error">Thời lượng phải từ 5 phút đến 8 giờ.</small>}{!invalidGapRange && !outsideClinicHours && !currentGapConflict && scheduleLoaded && !scheduleBusy && <small className="cw-booking-field-state">Khung giờ đã được kiểm tra với lịch mới nhất của bác sĩ.</small>}</label>
          <p className="cw-booking-wide cw-booking-field-state">{scheduleBusy ? loading('Đang kiểm tra lịch bác sĩ trực tiếp…') : scheduleLoaded ? (freeWindows(date, daySchedules).length ? 'Khoảng giờ còn trống: ' + freeWindows(date, daySchedules).join(' · ') + '. Nghỉ trưa 12:00–13:00.' : 'Bác sĩ không còn khoảng trống trong giờ khám 08:00–18:00.') : 'Chọn bác sĩ và ngày khám để tải lịch.'}</p>
        </>}
        {consultationCase && <p className="cw-booking-wide cw-booking-field-state">Phiếu theo buổi khám chỉ nhận lịch đã công bố thuộc buổi đó.</p>}
        <h3 className="cw-booking-step-title">2. Xác nhận thông tin phiếu khám</h3>
        <label>Họ tên bệnh nhân<input required maxLength={200} value={patientName} readOnly={!guest} disabled={!appointmentReady} onChange={e => setPatientName(e.target.value)} /></label>
        <label>Số điện thoại<input type="tel" value={patientPhone} readOnly={!guest} disabled={!appointmentReady} onChange={e => setPatientPhone(e.target.value)} /></label>
        <label>Email<input type="email" maxLength={320} value={patientEmail} readOnly={!guest} disabled={!appointmentReady} onChange={e => setPatientEmail(e.target.value)} /></label>
        <label>Ngày sinh<input type="date" value={birthDate} readOnly={!guest} disabled={!appointmentReady} onChange={e => setBirthDate(e.target.value)} /></label>
        <label>Giới tính<input maxLength={16} value={gender} readOnly={!guest} disabled={!appointmentReady} onChange={e => setGender(e.target.value)} /></label>
        <label>Hình thức khám<select disabled={!appointmentReady} value={encounterType} onChange={e => setEncounterType(e.target.value as 'in_person' | 'telehealth')}><option value="in_person">Trực tiếp</option><option value="telehealth">Từ xa</option></select></label>
        <label className="cw-booking-wide">Lý do khám<textarea required maxLength={2000} value={reason} disabled={!appointmentReady} onChange={e => setReason(e.target.value)} />{!appointmentReady && <small className="cw-booking-field-state">Chọn giờ khám trước để xác nhận booking.</small>}</label>
        <label className="cw-booking-wide">Ghi chú cho bác sĩ<textarea maxLength={2000} value={patientNote} disabled={!appointmentReady} onChange={e => setPatientNote(e.target.value)} /></label>
        <label className="cw-booking-consent"><input required type="checkbox" checked={agreed} disabled={!appointmentReady} onChange={e => setAgreed(e.target.checked)} />Bệnh nhân đã đồng ý thông tin và giờ khám trên booking này.</label>
      </div>
      <footer><button type="button" disabled={busy} onClick={onClose}>Để sau</button><button className="cw-btn-primary-claim" disabled={busy || !appointmentReady || !patientName.trim() || !catalog || catalogBusy || doctorBusy || scheduleBusy || !specialty || !agreed || !reason.trim()}>{busy ? 'Đang xác nhận…' : 'Xác nhận và tạo booking'}</button></footer>
    </form>
  </dialog>
}
