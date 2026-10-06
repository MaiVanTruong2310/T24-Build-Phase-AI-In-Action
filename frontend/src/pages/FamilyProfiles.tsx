import { useEffect, useState, type FormEvent } from 'react'
import { useSelector } from 'react-redux'
import { Link } from 'react-router-dom'
import type { RootState } from '../app/store'
import { vietnamToday } from '../features/appointment-booking/dateValidation'
import { addPatientProfile, editPatientProfile, archivePatientProfile, fetchPatientProfiles, relationshipNames, type PatientProfile, type RelativeInput } from '../features/patient-profiles/api'

const empty: RelativeInput = { full_name: '', date_of_birth: '', gender: '', relationship: 'parent', contact_phone: '', consent_to_manage: false }
export default function FamilyProfiles() {
  const user = useSelector((state: RootState) => state.auth.user)
  const [profiles, setProfiles] = useState<PatientProfile[]>([])
  const [draft, setDraft] = useState<RelativeInput>({ ...empty, contact_phone: user?.phone || '' })
  const [editing, setEditing] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const load = async () => setProfiles(await fetchPatientProfiles())
  useEffect(() => { let active = true; fetchPatientProfiles().then(items => { if (active) setProfiles(items) }).catch(e => { if (active) setError(e.message) }); return () => { active = false } }, [user?.id])
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault(); if (busy) return
    setBusy(true); setError(''); setNotice('')
    try {
      const payload = { ...draft, full_name: draft.full_name.trim(), citizen_id: draft.citizen_id || undefined, health_insurance_code: draft.health_insurance_code || undefined, address: draft.address || undefined }
      if (editing) await editPatientProfile(editing, payload); else await addPatientProfile(payload)
      setNotice(editing ? 'Đã cập nhật hồ sơ.' : 'Đã thêm người thân. Bạn có thể chọn hồ sơ này trong chatbot hoặc trang đặt khám.')
      setDraft({ ...empty, contact_phone: user?.phone || '' }); setEditing(''); await load()
    } catch (e) { setError(e instanceof Error ? e.message : 'Không thể lưu hồ sơ.') } finally { setBusy(false) }
  }
  async function archive(id: string) {
    if (busy || !window.confirm('Gỡ hồ sơ khỏi danh sách đặt khám? Lịch sử đã tạo vẫn được giữ lại.')) return
    setBusy(true); setError('')
    try { await archivePatientProfile(id); await load() } catch (e) { setError(e instanceof Error ? e.message : 'Không thể gỡ hồ sơ.') } finally { setBusy(false) }
  }
  const field = (key: keyof RelativeInput, value: string) => setDraft(d => ({ ...d, [key]: value }))
  return <div className="mx-auto max-w-4xl space-y-5 p-4">
    <h1 className="text-2xl font-bold">Hồ sơ người thân</h1>
    <p>Người thân có hồ sơ khám riêng và không cần tài khoản đăng nhập. Bạn nhận thông báo về các phiếu mình đặt.</p>
    {error && <p role="alert" className="text-red-600">{error}</p>}{notice && <p role="status" className="text-green-700">{notice}</p>}
    <div className="grid gap-3 sm:grid-cols-2">{profiles.map(p => <article key={p.id} className="rounded-xl border p-4">
      <h2 className="font-bold">{p.full_name || 'Chưa có tên'} · {relationshipNames[p.relationship]}</h2><p>Ngày sinh: {p.date_of_birth || 'Chưa bổ sung'}</p><p>Liên hệ: {p.contact_phone || 'Chưa bổ sung'}</p>
      {p.is_self ? <Link className="text-blue-600 underline" to="/patient/profile">Sửa hồ sơ bản thân</Link> : <div className="mt-2 flex gap-4"><button disabled={busy} onClick={() => { setEditing(p.id); setDraft({ full_name: p.full_name, date_of_birth: p.date_of_birth || '', gender: p.gender || '', relationship: p.relationship, contact_phone: p.contact_phone || '', citizen_id: p.citizen_id || '', health_insurance_code: p.health_insurance_code || '', address: p.address || '', consent_to_manage: false }) }}>Sửa</button><button disabled={busy} onClick={() => void archive(p.id)}>Gỡ hồ sơ</button></div>}
    </article>)}</div>
    <form onSubmit={submit} className="space-y-4 rounded-xl border p-4">
      <h2 className="text-lg font-bold">{editing ? 'Sửa hồ sơ người thân' : 'Thêm người thân'}</h2>
      <div className="grid gap-3 sm:grid-cols-2">
        <label>Họ tên *<input required minLength={2} maxLength={120} className="mt-1 w-full rounded border p-2" value={draft.full_name} onChange={e => field('full_name', e.target.value)} /></label>
        <label>Ngày sinh *<input type="date" required min="1900-01-01" max={vietnamToday()} className="mt-1 w-full rounded border p-2" value={draft.date_of_birth} onChange={e => field('date_of_birth', e.target.value)} /></label>
        <label>Giới tính *<select required className="mt-1 w-full rounded border p-2" value={draft.gender} onChange={e => field('gender', e.target.value)}><option value="">Chọn giới tính</option><option value="male">Nam</option><option value="female">Nữ</option><option value="other">Khác</option><option value="prefer_not_to_say">Không muốn cung cấp</option></select></label>
        <label>Quan hệ với bạn *<select className="mt-1 w-full rounded border p-2" value={draft.relationship} onChange={e => field('relationship', e.target.value)}>{Object.entries(relationshipNames).filter(([key]) => key !== 'self').map(([key,name]) => <option key={key} value={key}>{name}</option>)}</select></label>
        <label>Số điện thoại liên hệ *<input type="tel" required maxLength={20} className="mt-1 w-full rounded border p-2" value={draft.contact_phone} onChange={e => field('contact_phone', e.target.value)} /></label>
        <label>CCCD (nếu có)<input inputMode="numeric" pattern="[0-9]{12}" maxLength={12} className="mt-1 w-full rounded border p-2" value={draft.citizen_id || ''} onChange={e => field('citizen_id', e.target.value)} /></label>
        <label>Mã BHYT (nếu có)<input maxLength={32} className="mt-1 w-full rounded border p-2" value={draft.health_insurance_code || ''} onChange={e => field('health_insurance_code', e.target.value)} /></label>
        <label>Địa chỉ<input maxLength={500} className="mt-1 w-full rounded border p-2" value={draft.address || ''} onChange={e => field('address', e.target.value)} /></label>
      </div>
      <label className="flex gap-2"><input type="checkbox" required checked={draft.consent_to_manage} onChange={e => setDraft(d => ({ ...d, consent_to_manage: e.target.checked }))} />Tôi xác nhận được người khám hoặc người giám hộ đồng ý tạo và quản lý hồ sơ đặt lịch này.</label>
      <p className="text-sm text-slate-500">Quyền đặt lịch không tự cấp quyền xem bệnh án của một tài khoản khác.</p>
      <button disabled={busy} className="rounded bg-blue-700 px-4 py-2 text-white">{busy ? 'Đang lưu…' : 'Lưu hồ sơ'}</button>
      {editing && <button type="button" className="ml-3" onClick={() => { setEditing(''); setDraft({ ...empty, contact_phone: user?.phone || '' }) }}>Hủy sửa</button>}
    </form>
    <Link className="text-blue-600 underline" to="/patient/appointments">Đặt khám cho người thân</Link>
  </div>
}
