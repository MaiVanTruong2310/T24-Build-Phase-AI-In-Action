import type { DoctorForm, FacilityAssignmentForm } from './FormTypes'
import type { Specialty } from '../api'
import type { Facility } from '../../../features/appointment-booking/api'

interface Props {
  form: DoctorForm
  onChange: (field: keyof DoctorForm, value: string) => void
  specialties: Specialty[]
  facilities: Facility[]
  selectedSpecialties: string[]
  onSpecialtiesChange: (values: string[]) => void
  assignments: FacilityAssignmentForm[]
  onAssignmentsChange: (values: FacilityAssignmentForm[]) => void
}

const emptyAssignment = (): FacilityAssignmentForm => ({
  facility_id: '', department: '', room: '', position: '', active_from: '', active_to: '', is_primary: false,
})

export function OrganizationSection({ form, onChange, specialties, facilities, selectedSpecialties,
  onSpecialtiesChange, assignments, onAssignmentsChange }: Props) {
  const update = (index: number, patch: Partial<FacilityAssignmentForm>) => {
    const next = assignments.map((item, i) => i === index ? { ...item, ...patch } : { ...item })
    if (patch.is_primary) next.forEach((item, i) => { item.is_primary = i === index })
    onAssignmentsChange(next)
    if (patch.facility_id && index === 0) onChange('facility', facilities.find(x => x.id === patch.facility_id)?.name || '')
  }
  return <section className="mb-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
    <h2 className="text-lg font-bold">3. Chuyên khoa và nơi làm việc</h2>
    <p className="mt-1 text-sm text-slate-500">Một bác sĩ có thể làm tại nhiều cơ sở. Khoa, phòng và thời hạn được lưu riêng cho từng nơi.</p>
    <div className="mt-5">
      <p className="text-sm font-semibold">Chuyên khoa</p>
      <div className="mt-2 flex max-h-44 flex-wrap gap-2 overflow-y-auto">
        {specialties.map(item => <label key={item.id} className="flex items-center gap-2 rounded-lg border px-3 py-2 text-sm">
          <input type="checkbox" checked={selectedSpecialties.includes(item.id)} onChange={event => {
            const next = event.target.checked ? [...selectedSpecialties, item.id] : selectedSpecialties.filter(id => id !== item.id)
            onSpecialtiesChange(next)
            onChange('specialty', next[0] || '')
          }} />{item.name}
        </label>)}
      </div>
    </div>
    <div className="mt-6 space-y-4">
      <div className="flex items-center justify-between"><h3 className="text-sm font-semibold">Cơ sở công tác</h3>
        <button type="button" onClick={() => onAssignmentsChange([...assignments, emptyAssignment()])} className="rounded-lg border border-sky-300 px-3 py-2 text-sm font-semibold text-sky-700">+ Thêm cơ sở</button>
      </div>
      {assignments.map((item, index) => <div key={index} className="rounded-xl border bg-slate-50 p-4">
        <div className="grid gap-3 md:grid-cols-2">
          <label className="text-sm">Cơ sở<select required value={item.facility_id} onChange={event => update(index, { facility_id: event.target.value })} className="mt-1 w-full rounded-lg border bg-white p-2"><option value="">Chọn cơ sở</option>{facilities.map(f => <option key={f.id} value={f.id}>{f.name}</option>)}</select></label>
          <label className="text-sm">Khoa / trung tâm<input value={item.department} onChange={event => update(index, { department: event.target.value })} className="mt-1 w-full rounded-lg border p-2" placeholder="Ví dụ: Trung tâm Tiêu hóa" /></label>
          <label className="text-sm">Chức vụ tại cơ sở<input value={item.position} onChange={event => update(index, { position: event.target.value })} className="mt-1 w-full rounded-lg border p-2" placeholder="Ví dụ: Trưởng khoa" /></label>
          <label className="text-sm">Phòng khám<input value={item.room} onChange={event => update(index, { room: event.target.value })} className="mt-1 w-full rounded-lg border p-2" /></label>
          <label className="text-sm">Từ ngày<input type="date" value={item.active_from} onChange={event => update(index, { active_from: event.target.value })} className="mt-1 w-full rounded-lg border p-2" /></label>
          <label className="text-sm">Đến ngày<input type="date" value={item.active_to} onChange={event => update(index, { active_to: event.target.value })} className="mt-1 w-full rounded-lg border p-2" /></label>
        </div>
        <div className="mt-3 flex items-center justify-between"><label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={item.is_primary} onChange={event => update(index, { is_primary: event.target.checked })} />Cơ sở chính</label><button type="button" onClick={() => onAssignmentsChange(assignments.filter((_, i) => i !== index))} className="text-sm font-semibold text-red-700">Xóa cơ sở</button></div>
      </div>)}
      {assignments.length === 0 && <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">Chưa gán cơ sở. Bác sĩ sẽ không xuất hiện khi tìm kiếm theo cơ sở hoặc được công bố lịch khám.</p>}
    </div>
    <label className="mt-5 block text-sm">Chức vụ chung<input value={form.position} onChange={event => onChange('position', event.target.value)} className="mt-1 w-full rounded-lg border p-2" /></label>
  </section>
}
