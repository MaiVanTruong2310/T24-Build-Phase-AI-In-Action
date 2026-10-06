import { useSelector } from 'react-redux'
import { Link } from 'react-router-dom'
import type { RootState } from '../../app/store'
import { relationshipNames } from './api'
import type { PatientSelection } from './usePatientSelection'

export function PatientSelector({ selection, disabled = false }: { selection: PatientSelection; disabled?: boolean }) {
  const user = useSelector((state: RootState) => state.auth.user)
  if (user?.role !== 'patient') return null
  const profile = selection.selectedProfile
  const incomplete = !profile && (!user.full_name || !user.phone || !user.date_of_birth || !user.gender)
  return <section className="rounded-xl border border-slate-200 bg-white p-3 text-slate-900 dark:bg-slate-900 dark:text-white">
    <label className="block text-sm font-semibold">Bạn đang tư vấn / đặt khám cho ai?
      <select className="mt-2 w-full rounded border p-2 dark:bg-slate-800" value={selection.profileId} disabled={disabled || selection.loading} onChange={e => selection.choose(e.target.value)}>
        <option value="">Bản thân — {user.full_name}</option>
        {selection.profiles.filter(p => !p.is_self).map(p => <option key={p.id} value={p.id}>{p.full_name} · {relationshipNames[p.relationship] || p.relationship}</option>)}
      </select>
    </label>
    {profile && <p className="mt-2 text-sm">Người khám: {profile.full_name} · Ngày sinh: {profile.date_of_birth} · Liên hệ: {profile.contact_phone}</p>}
    {incomplete && <p role="alert" className="mt-2 text-sm text-amber-700">Hồ sơ bản thân còn thiếu thông tin. <Link className="underline" to="/patient/profile">Bổ sung hồ sơ trước khi đặt khám</Link>.</p>}
    {selection.error && <p role="alert" className="text-sm text-red-600">{selection.error}</p>}
    <Link className="mt-2 inline-block text-sm text-blue-600 underline" to="/patient/family">Thêm / quản lý hồ sơ người thân</Link>
  </section>
}
