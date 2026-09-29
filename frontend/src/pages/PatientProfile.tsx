import { FormEvent, useEffect, useState } from 'react';
import { Loader2, Save, UserRound } from 'lucide-react';
import { fetchCurrentUser, PatientProfile as PatientProfileData, updateCurrentUser } from '../features/patient/api';

const emptyProfile: PatientProfileData = {
  id: '',
  email: null,
  phone: null,
  role: 'patient',
  status: 'active',
  full_name: '',
  date_of_birth: null,
  gender: null,
  citizen_id: null,
  health_insurance_code: null,
};

export default function PatientProfile() {
  const [profile, setProfile] = useState(emptyProfile);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetchCurrentUser()
      .then(setProfile)
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Không thể tải hồ sơ'))
      .finally(() => setLoading(false));
  }, []);

  const updateField = (field: keyof PatientProfileData, value: string) => {
    setProfile((current) => ({ ...current, [field]: value || null }));
    setSaved(false);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    setSaved(false);
    try {
      const updated = await updateCurrentUser({
        full_name: profile.full_name,
        date_of_birth: profile.date_of_birth,
        gender: profile.gender,
        citizen_id: profile.citizen_id,
        health_insurance_code: profile.health_insurance_code,
      });
      setProfile(updated);
      setSaved(true);
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : 'Không thể cập nhật hồ sơ');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="rounded-2xl bg-white p-8 text-sm text-slate-500">Đang tải hồ sơ...</div>;
  }

  return (
    <section className="mx-auto max-w-3xl rounded-2xl border border-slate-200 bg-white p-6 shadow-sm md:p-8">
      <div className="mb-8 flex items-center gap-3">
        <div className="rounded-xl bg-sky-100 p-3 text-sky-700"><UserRound className="h-6 w-6" /></div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-sky-600">Hồ sơ bệnh nhân</p>
          <h1 className="text-2xl font-bold text-slate-900">Thông tin cá nhân</h1>
        </div>
      </div>

      {(error || saved) && (
        <div className={`mb-5 rounded-xl border p-3 text-sm ${error ? 'border-red-100 bg-red-50 text-red-700' : 'border-emerald-100 bg-emerald-50 text-emerald-700'}`}>
          {error || 'Hồ sơ đã được cập nhật.'}
        </div>
      )}

      <form className="grid gap-5 md:grid-cols-2" onSubmit={submit}>
        <label className="text-sm font-semibold text-slate-700">
          Họ và tên
          <input className="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" value={profile.full_name || ''} onChange={(event) => updateField('full_name', event.target.value)} maxLength={200} />
        </label>
        <label className="text-sm font-semibold text-slate-700">
          Ngày sinh
          <input className="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" type="date" value={profile.date_of_birth || ''} onChange={(event) => updateField('date_of_birth', event.target.value)} />
        </label>
        <label className="text-sm font-semibold text-slate-700">
          Giới tính
          <select className="mt-1.5 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 font-normal" value={profile.gender || ''} onChange={(event) => updateField('gender', event.target.value)}>
            <option value="">Chưa cập nhật</option>
            <option value="male">Nam</option>
            <option value="female">Nữ</option>
            <option value="other">Khác</option>
            <option value="unspecified">Không muốn tiết lộ</option>
          </select>
        </label>
        <label className="text-sm font-semibold text-slate-700">
          Email
          <input className="mt-1.5 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 font-normal text-slate-500" value={profile.email || 'Chưa cập nhật'} readOnly />
        </label>
        <label className="text-sm font-semibold text-slate-700">
          CCCD (12 số)
          <input className="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" type="password" inputMode="numeric" pattern="\d{12}" value={profile.citizen_id || ''} onChange={(event) => updateField('citizen_id', event.target.value.replace(/\D/g, '').slice(0, 12))} />
        </label>
        <label className="text-sm font-semibold text-slate-700">
          Mã bảo hiểm y tế
          <input className="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal" type="password" value={profile.health_insurance_code || ''} onChange={(event) => updateField('health_insurance_code', event.target.value.slice(0, 32))} maxLength={32} />
        </label>
        <div className="md:col-span-2 flex justify-end">
          <button className="inline-flex items-center gap-2 rounded-xl bg-sky-700 px-5 py-2.5 font-semibold text-white hover:bg-sky-800 disabled:cursor-not-allowed disabled:bg-slate-300" disabled={saving} type="submit">
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            Lưu thay đổi
          </button>
        </div>
      </form>
    </section>
  );
}
