import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import * as E from 'fp-ts/Either'
import { fetchFacilities } from '../../../features/appointment-booking/api'
import type { Facility } from '../../../features/appointment-booking/api'
import { createDoctor, fetchSpecialties, fetchStaffDoctor, updateStaffDoctor } from '../api'
import type { Specialty } from '../api'
import { OrganizationSection } from './OrganizationSection'
import type { DoctorForm, FacilityAssignmentForm } from './FormTypes'

const splitComma = (value: string) => value.split(',').map(x => x.trim()).filter(Boolean)
const splitLines = (value: string) => value.split('\n').map(x => x.trim()).filter(Boolean)

export default function CreateDoctor() {
  const navigate = useNavigate()
  const { id: doctorId } = useParams()
  const [form, setForm] = useState<DoctorForm>({
    fullName: '', academicTitle: '', gender: '', dateOfBirth: '', idNumber: '', phone: '', email: '',
    licenseNumber: '', licenseIssueDate: '', licenseIssuer: '', practiceScope: '', experienceYears: '',
    facility: '', specialty: '', position: '', defaultRoom: '', permissionLevel: 'level1',
    standardPrice: '', vipPrice: '', allowOnlineBooking: true, enableEmergencyCode: false,
  })
  const [specialties, setSpecialties] = useState<Specialty[]>([])
  const [facilities, setFacilities] = useState<Facility[]>([])
  const [selectedSpecialties, setSelectedSpecialties] = useState<string[]>([])
  const [assignments, setAssignments] = useState<FacilityAssignmentForm[]>([])
  const [honors, setHonors] = useState('')
  const [ranks, setRanks] = useState('')
  const [degrees, setDegrees] = useState('')
  const [languages, setLanguages] = useState('Tiếng Việt')
  const [education, setEducation] = useState('')
  const [workHistory, setWorkHistory] = useState('')
  const [awards, setAwards] = useState('')
  const [professionalRole, setProfessionalRole] = useState('Bác sĩ')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    void Promise.all([fetchSpecialties()(), fetchFacilities()]).then(([s, f]) => {
      if (E.isRight(s)) setSpecialties(s.right)
      else setError('Không tải được danh mục chuyên khoa.')
      setFacilities(f)
    }).catch(() => setError('Không tải được danh mục cơ sở.'))
  }, [])
  useEffect(() => {
    if (!doctorId) return
    void fetchStaffDoctor(doctorId).then(doctor => {
      setForm(previous => ({ ...previous, fullName: doctor.full_name, academicTitle: doctor.title || '', practiceScope: doctor.bio || '',
        experienceYears: doctor.experience_years?.toString() || '', position: doctor.position || '',
        allowOnlineBooking: doctor.booking_enabled }))
      setSelectedSpecialties(doctor.specialty_ids || [])
      setAssignments(doctor.facilities.map(item => ({ facility_id: item.facility_id,
        department: item.department || '', room: item.room || '', position: item.position || '',
        active_from: item.active_from || '', active_to: item.active_to || '', is_primary: item.is_primary || false })))
      setHonors(doctor.honors.join(', ')); setRanks(doctor.academic_ranks.join(', '))
      setDegrees(doctor.degrees.join(', ')); setLanguages(doctor.languages.join(', '))
      setEducation(doctor.education.join('\n')); setWorkHistory(doctor.work_history.join('\n'))
      setAwards(doctor.awards.join('\n'))
      setProfessionalRole(doctor.professional_role || 'Bác sĩ')
    }).catch(() => setError('Không thể tải hồ sơ bác sĩ để chỉnh sửa.'))
  }, [doctorId])

  const onChange = (field: keyof DoctorForm, value: string) => setForm(previous => ({ ...previous, [field]: value }))
  const save = async () => {
    setError('')
    const selectedFacilities = assignments.filter(x => x.facility_id)
    if (!form.fullName.trim() || selectedSpecialties.length === 0 || selectedFacilities.length === 0) {
      setError('Nhập tên, ít nhất một chuyên khoa và một cơ sở công tác.')
      return
    }
    if (new Set(selectedFacilities.map(x => x.facility_id)).size !== selectedFacilities.length || selectedFacilities.length !== assignments.length) {
      setError('Mỗi cơ sở chỉ được chọn một lần và không được để trống.')
      return
    }
    if (assignments.some(x => x.active_from && x.active_to && x.active_to < x.active_from)) {
      setError('Ngày kết thúc công tác phải sau ngày bắt đầu.')
      return
    }
    setBusy(true)
    const payload = {
      ...(!doctorId ? { code: `DOC-${Date.now()}` } : {}),
      full_name: form.fullName.trim(), bio: form.practiceScope.trim() || null,
      title: [...splitComma(honors), ...splitComma(ranks), ...splitComma(degrees)].join(' ').slice(0, 64) || form.academicTitle || null,
      honors: splitComma(honors), academic_ranks: splitComma(ranks), degrees: splitComma(degrees),
      languages: splitComma(languages), position: form.position.trim() || null,
      experience_years: form.experienceYears ? Number(form.experienceYears) : null,
      education: splitLines(education), work_history: splitLines(workHistory), awards: splitLines(awards),
      professional_role: professionalRole,
      ...(!doctorId ? { status: 'active', review_status: 'approved' } : {}), booking_enabled: professionalRole === 'Bác sĩ' && form.allowOnlineBooking,
      specialty_ids: selectedSpecialties,
      facilities: assignments.map(x => ({
        facility_id: x.facility_id, department: x.department.trim() || null,
        room: x.room.trim() || null, position: x.position.trim() || null,
        active_from: x.active_from || null, active_to: x.active_to || null, is_primary: x.is_primary,
      })),
      ...(!doctorId ? { service_ids: [] } : {}),
    }
    try {
      if (doctorId) await updateStaffDoctor(doctorId, payload)
      else {
        const result = await createDoctor(payload)()
        if (E.isLeft(result)) throw result.left
      }
      navigate('/staff/doctors')
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Không thể lưu hồ sơ bác sĩ.') }
    finally { setBusy(false) }
  }

  return <main className="min-h-screen bg-slate-50 p-4 md:p-8">
    <div className="mx-auto max-w-5xl space-y-6">
      <header><p className="text-sm text-slate-500">Quản lý bác sĩ</p><h1 className="mt-1 text-2xl font-bold">{doctorId ? 'Chỉnh sửa hồ sơ bác sĩ' : 'Thêm hồ sơ bác sĩ'}</h1><p className="mt-2 text-sm text-slate-600">Nhập thông tin chuyên môn có cấu trúc để bệnh nhân có thể tìm đúng bác sĩ và cơ sở.</p></header>
      {error && <p role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</p>}
      <section className="rounded-xl border bg-white p-6 shadow-sm"><h2 className="font-bold">1. Thông tin hiển thị</h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <label className="text-sm">Họ tên *<input value={form.fullName} onChange={e => onChange('fullName', e.target.value)} className="mt-1 w-full rounded-lg border p-2" /></label>
          <label className="text-sm">Nghề nghiệp<select value={professionalRole} onChange={e => setProfessionalRole(e.target.value)} className="mt-1 w-full rounded-lg border p-2"><option>Bác sĩ</option><option>Dược sĩ</option><option>Điều dưỡng</option><option>Kỹ thuật viên</option><option>Chuyên gia</option></select></label>
          <label className="text-sm">Số năm kinh nghiệm<input type="number" min="0" max="80" value={form.experienceYears} onChange={e => onChange('experienceYears', e.target.value)} className="mt-1 w-full rounded-lg border p-2" /></label>
          <label className="text-sm">Danh hiệu, cách nhau bằng dấu phẩy<input value={honors} onChange={e => setHonors(e.target.value)} placeholder="Thầy thuốc ưu tú" className="mt-1 w-full rounded-lg border p-2" /></label>
          <label className="text-sm">Học hàm, cách nhau bằng dấu phẩy<input value={ranks} onChange={e => setRanks(e.target.value)} placeholder="Phó giáo sư" className="mt-1 w-full rounded-lg border p-2" /></label>
          <label className="text-sm">Học vị / chuyên khoa<input value={degrees} onChange={e => setDegrees(e.target.value)} placeholder="Thạc sĩ, Bác sĩ chuyên khoa II" className="mt-1 w-full rounded-lg border p-2" /></label>
          <label className="text-sm">Ngôn ngữ tư vấn<input value={languages} onChange={e => setLanguages(e.target.value)} placeholder="Tiếng Việt, Tiếng Anh" className="mt-1 w-full rounded-lg border p-2" /></label>
        </div>
        <label className="mt-4 block text-sm">Giới thiệu chuyên môn<textarea rows={4} value={form.practiceScope} onChange={e => onChange('practiceScope', e.target.value)} className="mt-1 w-full rounded-lg border p-2" /></label>
      </section>
      <OrganizationSection form={form} onChange={onChange} specialties={specialties} facilities={facilities}
        selectedSpecialties={selectedSpecialties} onSpecialtiesChange={setSelectedSpecialties}
        assignments={assignments} onAssignmentsChange={setAssignments} />
      <section className="rounded-xl border bg-white p-6 shadow-sm"><h2 className="font-bold">4. Hồ sơ chuyên môn</h2><p className="mt-1 text-sm text-slate-500">Mỗi dòng là một mục riêng trong hồ sơ.</p>
        <div className="mt-4 grid gap-4 md:grid-cols-3">
          <label className="text-sm">Quá trình đào tạo<textarea rows={7} value={education} onChange={e => setEducation(e.target.value)} className="mt-1 w-full rounded-lg border p-2" /></label>
          <label className="text-sm">Kinh nghiệm làm việc<textarea rows={7} value={workHistory} onChange={e => setWorkHistory(e.target.value)} className="mt-1 w-full rounded-lg border p-2" /></label>
          <label className="text-sm">Giải thưởng / thành tựu<textarea rows={7} value={awards} onChange={e => setAwards(e.target.value)} className="mt-1 w-full rounded-lg border p-2" /></label>
        </div>
      </section>
      <div className="flex items-center justify-end gap-3"><button type="button" onClick={() => navigate('/staff/doctors')} className="rounded-lg border px-5 py-3">Hủy</button><button type="button" disabled={busy} onClick={() => void save()} className="rounded-lg bg-sky-700 px-5 py-3 font-semibold text-white disabled:opacity-50">{busy ? 'Đang lưu…' : 'Lưu hồ sơ bác sĩ'}</button></div>
    </div>
  </main>
}
